"""Catalog reality scanner.

Ported from Orkestra (core/catalog_scanner.py + core/sitemap_aov_scraper.py) —
the battle-tested parts only: Shopify /products.json with full pagination,
sitemap.xml fallback, locale-aware money parsing, product name normalization.

Purpose in AGORA: fetch the merchant's *structured* catalog so the audit can
compare "what the store actually sells" against "what an agent can read from
the raw HTML". The gap between the two is the product-analysis pitch.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx

from .ssrf import SSRFError, pinned_get

_TIMEOUT = 8.0
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AGORA-Auditor/0.1)"}
# Shopify pagination: keep going until an empty page, hard safety cap
_MAX_PAGES = 20
_PAGE_LIMIT = 250
_PRODUCT_PATH_RE = re.compile(r"/(?:product|products|p|urun|urunler)/", re.IGNORECASE)
# A sitemap whose own filename announces it holds products (products.xml,
# urunler.xml, product-sitemap.xml). Every <loc> inside it is a product page by
# definition, so the per-URL path filter must be SKIPPED — platforms like ikas,
# ideasoft and ticimax use flat product URLs (/gamesir-t4-pro) with no
# /product/ path segment, and the path filter would silently drop all of them.
_PRODUCT_SITEMAP_RE = re.compile(r"(?:product|urun)", re.IGNORECASE)
# Obvious non-product pages that every storefront sitemap carries: policy,
# account, help and checkout routes. Used to prune a flat mixed sitemap before
# sampling, so the JSON-LD enrichment budget is not spent on CMS pages. Product
# slugs that happen to contain one of these tokens are rare and get restored by
# the enrichment step (which keeps only pages with schema.org/Product markup).
_CMS_URL_RE = re.compile(
    r"/(?:iletisim|hakkimizda|hakkinda|giris|uye|uyelik|kvkk|gizlilik|sozlesme|"
    r"kosul|kurallar|kargo|iade|degisim|teslimat|odeme|guvenlik|yardim|sss|"
    r"siparis|musteri-hizmetleri|magazalar|blog|hesap|favori|sepet|"
    r"about|contact|privacy|terms|shipping|return|faq|help|account|login|"
    r"register|cart|wishlist|checkout)",
    re.IGNORECASE,
)
# Strip the XML namespace prefix so tag matching works on every sitemap dialect.
_NS_STRIP = re.compile(r"^\{[^}]+\}")
_DOUBLE_SPACE_RE = re.compile(r" {2,}")


class CatalogSource(str, Enum):
    PRODUCTS_JSON = "products_json"
    SITEMAP = "sitemap"
    NONE = "none"


@dataclass(frozen=True)
class CatalogProduct:
    name: str
    url: str
    price: float | None = None


@dataclass
class CatalogScan:
    products: list[CatalogProduct] = field(default_factory=list)
    total_count: int = 0
    source: CatalogSource = CatalogSource.NONE

    @property
    def found(self) -> bool:
        return self.total_count > 0


# ── Domain / money / name helpers (Orkestra ports) ───────────────────────────

def normalize_domain(domain_or_url: str) -> str:
    """Strip scheme/path so we can build clean endpoint URLs."""
    raw = domain_or_url.strip()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0]
    return raw.removeprefix("www.").lower()


def parse_money_string(raw: str) -> float | None:
    """Locale-aware money parser. Handles Turkish and English formats.

    "1.299,90" → 1299.90 · "299,90" → 299.90 · "1,299.90" → 1299.90
    "1.299.000" → 1299000.0 · returns None on garbage, never raises.
    """
    s = raw.strip()
    if not s:
        return None

    has_dot = "." in s
    has_comma = "," in s
    if has_dot and has_comma:
        # The LAST separator is the decimal — universal heuristic.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")  # TR pattern
        else:
            s = s.replace(",", "")  # EN pattern; dot stays as decimal
    elif has_comma:
        parts = s.split(",")
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_dot:
        parts = s.split(".")
        if not (len(parts) == 2 and 1 <= len(parts[1]) <= 2):
            s = s.replace(".", "")

    try:
        return float(s)
    except ValueError:
        return None


def coerce_price(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        return parse_money_string(raw)
    return None


def normalize_product_name(name: str) -> str:
    """Clean a raw scrape title: collapse double spaces, close open parens."""
    if not name:
        return ""
    result = _DOUBLE_SPACE_RE.sub(" ", name.strip())
    open_count = result.count("(")
    close_count = result.count(")")
    if open_count > close_count:
        result += ")" * (open_count - close_count)
    return result


# ── Sitemap helpers ───────────────────────────────────────────────────────────

def _strip_ns(tag: str) -> str:
    return _NS_STRIP.sub("", tag)


def parse_sitemap_urls(xml_text: str) -> list[str]:
    """Extract page <loc> URLs from a sitemap or sitemapindex.

    Excludes the <image:loc>/<video:loc> entries of the sitemap image/video
    extensions: after the namespace strip those tags also read as "loc", so
    counting them would double the catalog size (ikas emits one image loc per
    product) and send the enrichment step off to fetch .webp files.

    Returns an empty list on malformed XML rather than raising — sitemap
    quality varies wildly across e-commerce themes."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    return [
        elem.text.strip()
        for elem in root.iter()
        if _strip_ns(elem.tag) == "loc"
        and "sitemap-image" not in elem.tag.lower()
        and "sitemap-video" not in elem.tag.lower()
        and elem.text
    ]


def is_sitemap_index(xml_text: str) -> bool:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return False
    return _strip_ns(root.tag).lower() == "sitemapindex"


def filter_product_urls(urls: list[str]) -> list[str]:
    """Keep only URLs that look like product detail pages."""
    return [u for u in urls if _PRODUCT_PATH_RE.search(u)]


def _looks_like_product_sitemap(sitemap_url: str) -> bool:
    """True when the sitemap's own path names it as a products feed.

    Matched on the path only (not the host) so a domain like producthub.com
    does not falsely mark every one of its sitemaps as product-bearing."""
    return bool(_PRODUCT_SITEMAP_RE.search(urlparse(sitemap_url).path))


def _sample_candidate_urls(
    urls: list[str], sample_size: int = None  # type: ignore[assignment]
) -> list[str]:
    """Pick a bounded, product-biased sample from a flat mixed sitemap.

    Turkish e-commerce platforms (Ticimax, ideasoft, ikas) publish one flat
    <urlset> where product URLs are slug-style (/hello-kitty-cuzdan) with no
    /urun/ or /product/ path segment, so `filter_product_urls` drops them all.
    Here we instead prune the obvious CMS/account/policy pages and the bare
    homepage, then take an evenly-strided sample. Products cluster in the tail
    (after CMS + category URLs), so striding — rather than taking the first N —
    lands the enrichment budget on real product pages. Category pages swept in
    by the stride carry no schema.org/Product markup and are discarded by the
    JSON-LD enrichment step downstream."""
    if sample_size is None:
        sample_size = _SITEMAP_ENRICH_LIMIT
    candidates = [
        u
        for u in urls
        if urlparse(u).path.strip("/") and not _CMS_URL_RE.search(urlparse(u).path)
    ]
    if len(candidates) <= sample_size:
        return candidates
    stride = len(candidates) / sample_size
    return [candidates[int(i * stride)] for i in range(sample_size)]


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await pinned_get(client, url)
    except (httpx.HTTPError, SSRFError):
        return None
    if resp.status_code != 200:
        return None
    return resp.text


async def _collect_all_product_urls(
    client: httpx.AsyncClient,
    sitemap_url: str,
    *,
    max_children: int = 8,
) -> tuple[list[str], bool]:
    """Resolve a sitemap entry point into product URLs.

    Returns (urls, confirmed). When confirmed is True every URL is known to be a
    product page (product-named sitemap or path-filter match), so the caller can
    trust len(urls) as the catalog size. When False the URLs are a product-biased
    *sample* of a flat mixed sitemap that must be JSON-LD-verified before any of
    them counts — the true total is unknown, so the caller reports only what it
    can verify. Handles both shapes served in the wild: flat <urlset> and
    <sitemapindex> (one recursion level, product-flavored children first)."""
    xml_text = await _fetch_text(client, sitemap_url)
    if not xml_text:
        return [], True

    if not is_sitemap_index(xml_text):
        locs = parse_sitemap_urls(xml_text)
        # A dedicated products feed lists only product pages, so keep every URL.
        if _looks_like_product_sitemap(sitemap_url):
            return locs, True
        filtered = filter_product_urls(locs)
        if filtered:
            return filtered, True
        # Flat mixed sitemap with slug-style product URLs (Ticimax/ideasoft/ikas):
        # the path filter matched nothing. Sample for JSON-LD verification instead
        # of giving up — otherwise the whole catalog is invisible to the audit.
        return _sample_candidate_urls(locs), False

    child_urls = parse_sitemap_urls(xml_text)
    child_urls.sort(key=lambda u: 0 if "product" in u.lower() else 1)
    aggregated: list[str] = []
    for child in child_urls[:max_children]:
        child_xml = await _fetch_text(client, child)
        if not child_xml:
            continue
        child_locs = parse_sitemap_urls(child_xml)
        if _looks_like_product_sitemap(child):
            aggregated.extend(child_locs)
        else:
            aggregated.extend(filter_product_urls(child_locs))
        if len(aggregated) >= 1000:
            break
    return aggregated, True


# ── JSON-LD product enrichment (non-Shopify sitemap sources) ─────────────────
# A sitemap gives product URLs but no names/prices. Non-Shopify platforms
# (ikas, ideasoft, ticimax) embed a schema.org/Product in each product page as
# JSON-LD, so we fetch a bounded sample and read name + price from that. Full
# catalog enrichment (all URLs) belongs to the paid install pipeline; the live
# audit samples enough to prove the gap (P-5 freemium split).
_SITEMAP_ENRICH_LIMIT = 24
_ENRICH_CONCURRENCY = 12
_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _iter_jsonld_objects(html: str):
    """Yield every JSON-LD dict in the page, flattening @graph and list roots."""
    for match in _JSONLD_RE.finditer(html):
        try:
            data = json.loads(match.group(1).strip())
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                graph = node.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
                yield node


def extract_product_jsonld(html: str) -> tuple[str | None, float | None]:
    """Pull (name, price) from the first schema.org/Product JSON-LD block.

    Handles @type as string or list, and offers as dict or list. Returns
    (None, None) when the page carries no product markup."""
    for node in _iter_jsonld_objects(html):
        raw_type = node.get("@type")
        types = raw_type if isinstance(raw_type, list) else [raw_type]
        if not any(isinstance(t, str) and t.lower() == "product" for t in types):
            continue
        name = node.get("name")
        if not (isinstance(name, str) and name.strip()):
            continue
        offers = node.get("offers")
        offer_list = offers if isinstance(offers, list) else [offers]
        price: float | None = None
        for offer in offer_list:
            if isinstance(offer, dict):
                price = coerce_price(offer.get("price") or offer.get("lowPrice"))
                if price is not None:
                    break
        return normalize_product_name(name), price
    return None, None


async def _enrich_products_from_pages(
    client: httpx.AsyncClient, urls: list[str]
) -> list[CatalogProduct]:
    """Fetch a bounded, concurrency-capped sample of product pages and read
    name + price from each page's JSON-LD. Order is preserved so the sample is
    the first N sitemap entries, not a random subset."""
    sample = urls[:_SITEMAP_ENRICH_LIMIT]
    semaphore = asyncio.Semaphore(_ENRICH_CONCURRENCY)

    async def fetch_one(url: str) -> CatalogProduct | None:
        async with semaphore:
            html = await _fetch_text(client, url)
        if not html:
            return None
        name, price = extract_product_jsonld(html)
        if not name:
            return None
        return CatalogProduct(name=name, url=url, price=price)

    results = await asyncio.gather(*(fetch_one(u) for u in sample))
    return [r for r in results if r is not None]


# ── Shopify /products.json (primary source) ──────────────────────────────────

async def _fetch_products_json_paginated(
    domain: str,
    client: httpx.AsyncClient,
) -> list[dict]:
    """Page through /products.json until an empty page. Empty list means the
    endpoint does not exist or the catalog is empty."""
    all_products: list[dict] = []
    for page in range(1, _MAX_PAGES + 1):
        url = f"https://{domain}/products.json?limit={_PAGE_LIMIT}&page={page}"
        try:
            resp = await pinned_get(client, url)
        except (httpx.HTTPError, SSRFError):
            break
        if resp.status_code != 200 or "json" not in resp.headers.get("content-type", ""):
            break
        try:
            data = resp.json()
        except ValueError:
            break
        if not isinstance(data, dict) or "products" not in data:
            break
        batch = data["products"]
        if not batch:
            break
        all_products.extend(batch)
        if len(batch) < _PAGE_LIMIT:
            break
    return all_products


def parse_shopify_products(products: list[dict], domain: str) -> list[CatalogProduct]:
    entries: list[CatalogProduct] = []
    for p in products:
        title = (p.get("title") or "").strip()
        if not title:
            continue
        handle = p.get("handle") or ""
        url = f"https://{domain}/products/{handle}" if handle else f"https://{domain}/"
        price: float | None = None
        for v in p.get("variants", []):
            c = coerce_price(v.get("price"))
            if c and c > 0 and (price is None or c < price):
                price = c
        entries.append(CatalogProduct(name=normalize_product_name(title), url=url, price=price))
    return entries


# ── Main scanner ──────────────────────────────────────────────────────────────

def _host_variants(domain_or_url: str, host: str) -> list[str]:
    """Both www and apex spellings of the host, caller's spelling tried first.

    scan_catalog fetches with redirects OFF (SSRF guard), but storefronts are
    canonical on exactly one of www/apex and 301 the other. Fetching only the
    www-stripped host silently loses every www-canonical store (the apex 301s to
    www and the redirect is dropped). Trying both self-computed spellings of the
    SAME registrable domain restores those catalogs without following any
    server-controlled redirect — so the SSRF guarantee is unchanged."""
    lower = domain_or_url.strip().lower()
    had_www = lower.startswith("www.") or "://www." in lower
    www, apex = f"www.{host}", host
    return [www, apex] if had_www else [apex, www]


async def _scan_single_host(client: httpx.AsyncClient, host: str) -> CatalogScan:
    """Run the /products.json → sitemap fallback against one host spelling."""
    try:
        raw_products = await _fetch_products_json_paginated(host, client)
    except Exception:
        raw_products = []

    if raw_products:
        entries = parse_shopify_products(raw_products, host)
        return CatalogScan(
            products=entries,
            total_count=len(entries),
            source=CatalogSource.PRODUCTS_JSON,
        )

    try:
        urls, confirmed = await _collect_all_product_urls(
            client, f"https://{host}/sitemap.xml"
        )
    except Exception:
        urls, confirmed = [], True

    if urls:
        # A sampled JSON-LD enrichment fills in names/prices so the llms.txt can
        # list real products instead of falling back to page markdown.
        try:
            products = await _enrich_products_from_pages(client, urls)
        except Exception:
            products = []
        if confirmed:
            # Path-verified product URLs: len(urls) is the true catalog size.
            total_count = len(urls)
        else:
            # Flat mixed sitemap: only the JSON-LD-verified sample is trusted.
            # No products confirmed → no catalog (fail-open), never guess a total.
            if not products:
                return CatalogScan()
            total_count = len(products)
        return CatalogScan(
            products=products,
            total_count=total_count,
            source=CatalogSource.SITEMAP,
        )

    return CatalogScan()


async def scan_catalog(domain_or_url: str) -> CatalogScan:
    """Fetch the structured catalog: /products.json first, sitemap fallback.

    Never raises — an unreachable or non-e-commerce site returns an empty
    scan so the audit stays fail-open."""
    host = normalize_domain(domain_or_url)

    # follow_redirects is OFF by design: scan_catalog only ever fetches paths it
    # constructs on the caller-validated host. Following a redirect could send the
    # request to an attacker-chosen host and bypass the SSRF guard, so a redirect
    # is treated as "no catalog here" (fail-open, consistent with the scanner).
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=False
    ) as client:
        for candidate_host in _host_variants(domain_or_url, host):
            scan = await _scan_single_host(client, candidate_host)
            if scan.found:
                return scan

    return CatalogScan()


# ── Agent visibility diff ─────────────────────────────────────────────────────

def count_visible_products(products: list[CatalogProduct], agent_text: str) -> int:
    """How many catalog product names an agent could actually find in the
    crawled page text. Whitespace-collapsed, case-insensitive containment —
    simple and explainable (P3)."""
    haystack = " ".join(agent_text.lower().split())
    visible = 0
    for p in products:
        needle = " ".join(p.name.lower().split())
        if needle and needle in haystack:
            visible += 1
    return visible
