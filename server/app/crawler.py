import logging
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .catalog import CatalogScan, count_visible_products, scan_catalog
from .ratelimit import limit_audit
from .ssrf import SSRFError, safe_get, safe_stream

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalyzeRequest(BaseModel):
    url: str


class ChecklistItem(BaseModel):
    pass_status: bool
    evidence: str


class Checklist(BaseModel):
    llms_txt: ChecklistItem
    product_content: ChecklistItem
    schema_org: ChecklistItem
    robots_txt: ChecklistItem


class CatalogProductOut(BaseModel):
    name: str
    url: str
    price: float | None = None


class CatalogInfo(BaseModel):
    """Catalog reality vs agent view — the product-analysis diff."""

    source: str  # products_json | sitemap | none
    total_count: int
    visible_to_agent: int
    coverage_pct: float
    sample: list[CatalogProductOut]


class AnalyzeResponse(BaseModel):
    url: str
    total_bytes: int
    script_ratio: float
    extractable_text_pct: float
    raw_html: str
    markdown: str
    # Preview only — the full generated file never leaves the server on the
    # public audit endpoint (P-5 freemium gate); it ships with the paid
    # install package.
    generated_llms_txt: str
    llms_txt_truncated: bool = False
    catalog: CatalogInfo | None = None
    checklist: Checklist


# --- HTML Parser for Metrics and Indicators ---
class HTMLContentAnalyzer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script_style_bytes = 0
        self.clean_text_bytes = 0
        self.in_script_style = False
        self.in_title = False
        self.page_title = ""
        self.has_schema_product = False
        self.product_tokens_found = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("script", "style"):
            self.in_script_style = True
        elif t == "title":
            self.in_title = True

        attrs_dict = dict(attrs)
        itemtype = attrs_dict.get("itemtype", "")
        if "schema.org/product" in itemtype.lower():
            self.has_schema_product = True

        # Check for JSON-LD script tag
        self.current_script_type = attrs_dict.get("type", "")

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style"):
            self.in_script_style = False
        elif t == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.page_title += data.strip()
        data_bytes_len = len(data.encode("utf-8"))
        if self.in_script_style:
            self.script_style_bytes += data_bytes_len
            # Check JSON-LD content for product
            if (
                hasattr(self, "current_script_type")
                and "ld+json" in self.current_script_type.lower()
            ):
                if '"@type": "product"' in data.lower() or '"@type":"product"' in data.lower():
                    self.has_schema_product = True
        else:
            cleaned = data.strip()
            if cleaned:
                self.clean_text_bytes += len(cleaned.encode("utf-8"))
                lower_val = cleaned.lower()
                for token in (
                    "price",
                    "add to cart",
                    "sepet",
                    "fiyat",
                    "stock",
                    "stok",
                    "cart",
                    "basket",
                    "in stock",
                    "out of stock",
                    "ürün",
                    "product",
                ):
                    if token in lower_val and token not in self.product_tokens_found:
                        self.product_tokens_found.append(token)
                # Simple Price Pattern check
                if re.search(r"[\$\d]+[\.,\d]*\s?(usd|tl|eur|try|\$|€|₺)", lower_val) or re.search(
                    r"(usd|tl|eur|try|\$|€|₺)\s?[\$\d]+[\.,\d]*", lower_val
                ):
                    if "price_pattern" not in self.product_tokens_found:
                        self.product_tokens_found.append("price_pattern")


# --- HTML to Markdown Parser ---
class HTMLToMarkdown(HTMLParser):
    def __init__(self):
        super().__init__()
        self.markdown_parts = []
        self.in_ignored_tag = False
        self.list_depth = 0
        self.list_type = []
        self.current_href = None
        # While inside <a>, text is buffered so nested markup / indentation
        # collapses to a single-line "[text](href)" instead of a broken link.
        self.link_text_parts: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("script", "style", "head", "noscript", "iframe", "nav"):
            self.in_ignored_tag = True
        elif t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(t[1])
            self.markdown_parts.append(f"\n\n{'#' * level} ")
        elif t in ("p", "div"):
            self.markdown_parts.append("\n\n")
        elif t == "br":
            self.markdown_parts.append("\n")
        elif t in ("ul", "ol"):
            self.list_depth += 1
            self.list_type.append(t)
            self.markdown_parts.append("\n")
        elif t == "li":
            indent = "  " * (self.list_depth - 1)
            marker = "- " if (not self.list_type or self.list_type[-1] == "ul") else "1. "
            self.markdown_parts.append(f"\n{indent}{marker}")
        elif t == "a":
            attrs_dict = dict(attrs)
            self.current_href = attrs_dict.get("href")
            self.link_text_parts = []
        elif t == "img":
            attrs_dict = dict(attrs)
            alt = attrs_dict.get("alt", "image")
            src = attrs_dict.get("src", "")
            if self.link_text_parts is not None:
                self.link_text_parts.append(alt)
            else:
                self.markdown_parts.append(f"![{alt}]({src})")

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style", "head", "noscript", "iframe", "nav"):
            self.in_ignored_tag = False
        elif t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.markdown_parts.append("\n\n")
        elif t in ("ul", "ol"):
            self.list_depth = max(0, self.list_depth - 1)
            if self.list_type:
                self.list_type.pop()
            self.markdown_parts.append("\n")
        elif t == "a":
            text = " ".join("".join(self.link_text_parts or []).split())
            if text:
                if self.current_href:
                    self.markdown_parts.append(f"[{text}]({self.current_href})")
                else:
                    self.markdown_parts.append(text)
            self.current_href = None
            self.link_text_parts = None

    def handle_data(self, data):
        if self.in_ignored_tag:
            return
        if self.link_text_parts is not None:
            self.link_text_parts.append(data)
        else:
            self.markdown_parts.append(data)

    def get_markdown(self) -> str:
        raw = "".join(self.markdown_parts)
        # Re-attach list markers to their content when block tags inside <li>
        # forced a line break ("- \n\ntext" → "- text").
        raw = re.sub(r"((?:^|\n)[ ]*(?:-|1\.)[ ])[ \t]*\n+[ \t]*", r"\1", raw)
        # Normalize whitespace: strip per-line tails, drop space-only lines,
        # then collapse blank-line runs — every junk line costs agent tokens.
        lines = [line.rstrip() for line in raw.split("\n")]
        raw = "\n".join(line if line.strip() else "" for line in lines)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


_LLMS_MAX_CONTENT_CHARS = 6000
_LLMS_MAX_CATALOG_PRODUCTS = 100

# A line "sells" something when it carries a price: "Price: $299", "449 TL",
# "Fiyat: 1.299,90₺"… Mentions of the words product/catalog alone don't count —
# Shopify's auto llms.txt talks ABOUT products without listing any.
_LLMS_PRICE_LINE_RE = re.compile(
    r"(\d[\d.,]*\s?(usd|eur|try|tl|\$|€|₺))"
    r"|((price|fiyat)\s*[:=]\s*\S)"
    r"|((\$|€|₺)\s?\d)",
    re.IGNORECASE,
)
_LLMS_MIN_PRICED_LINES = 2


def assess_llms_txt(text: str) -> tuple[bool, str]:
    """Judge whether an llms.txt actually serves the merchant's catalog.

    Returns (has_catalog, evidence). Discriminator is priced product lines,
    not keyword mentions: an instructions-only file (e.g. Shopify's
    auto-generated one pointing agents at UCP/Shop endpoints) says "products"
    everywhere yet lists none."""
    stripped = text.lstrip().lower()
    if stripped.startswith(("<!doctype", "<html")):
        return False, "URL returned an HTML page, not an llms.txt (likely soft-404)"

    priced_lines = sum(
        1 for line in text.splitlines() if _LLMS_PRICE_LINE_RE.search(line)
    )
    size = len(text.encode("utf-8"))
    if priced_lines >= _LLMS_MIN_PRICED_LINES:
        return True, f"Found /llms.txt ({size} bytes) with {priced_lines} priced product lines"
    return False, (
        f"Found /llms.txt ({size} bytes) but no priced product lines — "
        "agents get instructions, not your catalog"
    )


def generate_llms_txt(
    url: str, page_title: str, markdown: str, catalog: CatalogScan | None = None
) -> str:
    """Build a ready-to-host /llms.txt from the crawled page.

    Follows the llms.txt convention: H1 title, blockquote summary, then the
    machine-readable content — capped so the file stays token-cheap.
    When a structured catalog was scanned (Shopify /products.json), the
    Products section is built from real catalog entries instead of the page
    markdown: names, prices and canonical URLs the agent can trust."""
    host = urlparse(url).netloc or url
    title = page_title.strip() or host

    if catalog is not None and catalog.products:
        lines = []
        for p in catalog.products[:_LLMS_MAX_CATALOG_PRODUCTS]:
            price_part = f" — Price: {p.price:g}" if p.price is not None else ""
            lines.append(f"- [{p.name}]({p.url}){price_part}")
        remaining = catalog.total_count - min(len(catalog.products), _LLMS_MAX_CATALOG_PRODUCTS)
        if remaining > 0:
            lines.append(f"- …and {remaining} more products")
        content = f"## Products ({catalog.total_count})\n\n" + "\n".join(lines)
    else:
        content = markdown.strip()
        if len(content) > _LLMS_MAX_CONTENT_CHARS:
            content = content[:_LLMS_MAX_CONTENT_CHARS].rsplit("\n", 1)[0] + "\n\n…(truncated)"

    return (
        f"# {title}\n\n"
        f"> Machine-readable storefront summary generated by AGORA.\n"
        f"> Source: {url}\n\n"
        f"{content}\n"
    )


_LLMS_PREVIEW_PRODUCT_LINES = 10
_LLMS_PREVIEW_CONTENT_CHARS = 600


def make_llms_preview(full_text: str) -> tuple[str, bool]:
    """Truncate a generated llms.txt for the public audit response.

    The free audit proves the coverage gap; it must not hand out the full
    deliverable (P-5). Catalog-backed files keep the header plus the first
    few product lines; content-backed files keep a short prefix. Returns
    (preview, was_truncated). The full file is only produced server-side
    (generate_llms_txt) and delivered with the paid install package.
    """
    lines = full_text.splitlines()
    product_line_idx = [i for i, line in enumerate(lines) if line.startswith("- [")]

    if len(product_line_idx) > _LLMS_PREVIEW_PRODUCT_LINES:
        cut_at = product_line_idx[_LLMS_PREVIEW_PRODUCT_LINES]
        hidden = len(product_line_idx) - _LLMS_PREVIEW_PRODUCT_LINES
        preview_lines = lines[:cut_at]
        preview_lines.append(
            f"- …preview truncated: {hidden}+ more product lines in the full file, "
            "delivered with the AGORA install package."
        )
        return "\n".join(preview_lines) + "\n", True

    if len(full_text) > _LLMS_PREVIEW_CONTENT_CHARS:
        cut_text = full_text[:_LLMS_PREVIEW_CONTENT_CHARS].rsplit("\n", 1)[0]
        return (
            cut_text
            + "\n\n…preview truncated — the full file is delivered with the "
            "AGORA install package.\n"
        ), True

    return full_text, False


def parse_robots_txt(robots_content: str, path: str) -> tuple[bool, str]:
    """Parse robots.txt to check if known agent user-agents are blocked."""
    lines = [ln.strip().lower() for ln in robots_content.split("\n")]
    current_ua = None
    blocked_uas = []
    path_lower = path.lower()

    for line in lines:
        if not line or line.startswith("#"):
            continue
        if line.startswith("user-agent:"):
            current_ua = line.split(":", 1)[1].strip()
        elif line.startswith("disallow:") and current_ua:
            disallow_path = line.split(":", 1)[1].strip()
            if disallow_path:
                if disallow_path == "/" or path_lower.startswith(disallow_path):
                    blocked_uas.append(current_ua)

    known_agents = ["*", "gptbot", "perplexitybot", "claude-webcrawler", "bytespider", "googlebot"]
    blocked_known = [ua for ua in blocked_uas if ua in known_agents]
    if blocked_known:
        return False, f"Blocked: robots.txt disallows agent(s): {', '.join(blocked_known)}"
    return True, "robots.txt does not block known agent user-agents on this path"


_CRAWLER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 AGORA-Auditor/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
}


@router.post(
    "/report/analyze",
    response_model=AnalyzeResponse,
    dependencies=[Depends(limit_audit)],
)
async def analyze_url(req: AnalyzeRequest):
    url_str = req.url.strip()
    if not url_str:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        url_str = "https://" + url_str

    # Fetch page once (Timeout 8s, Size cap 2MB). safe_stream re-validates the
    # target and every redirect hop, so an attacker cannot use a public URL that
    # redirects to an internal address to bypass the SSRF guard (D007-R).
    try:
        async with httpx.AsyncClient(timeout=8.0, headers=_CRAWLER_HEADERS) as client:
            async with safe_stream(client, "GET", url_str) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > 2 * 1024 * 1024:
                    raise HTTPException(status_code=400, detail="Page size exceeds 2MB limit")

                chunks = []
                bytes_downloaded = 0
                async for chunk in response.aiter_bytes():
                    bytes_downloaded += len(chunk)
                    if bytes_downloaded > 2 * 1024 * 1024:
                        raise HTTPException(status_code=400, detail="Page size exceeds 2MB limit")
                    chunks.append(chunk)

                html_bytes = b"".join(chunks)
                html_content = html_bytes.decode("utf-8", errors="replace")
    except SSRFError as e:
        raise HTTPException(status_code=400, detail=f"Refused to fetch URL: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Target server returned error status {e.response.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Request failed: {str(e)}")

    total_bytes = len(html_bytes)

    # Analyze HTML for metrics & schema
    analyzer = HTMLContentAnalyzer()
    try:
        analyzer.feed(html_content)
    except Exception:
        pass  # Gracefully proceed with partial results if HTML parser breaks on invalid HTML

    # Compute metrics
    script_ratio = (
        round((analyzer.script_style_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0.0
    )
    extractable_text_pct = (
        round((analyzer.clean_text_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0.0
    )

    # Translate to markdown
    md_parser = HTMLToMarkdown()
    try:
        md_parser.feed(html_content)
        markdown = md_parser.get_markdown()
    except Exception:
        markdown = "Failed to parse content to markdown."

    # Catalog reality scan — structured ground truth vs what the agent read.
    # Fail-open: a site without /products.json or sitemap simply has no catalog block.
    catalog_info: CatalogInfo | None = None
    catalog_scan: CatalogScan | None = None
    try:
        catalog_scan = await scan_catalog(url_str)
        if catalog_scan.found:
            visible = count_visible_products(catalog_scan.products, markdown)
            coverage = (
                round(visible / len(catalog_scan.products) * 100, 1)
                if catalog_scan.products
                else 0.0
            )
            catalog_info = CatalogInfo(
                source=catalog_scan.source.value,
                total_count=catalog_scan.total_count,
                visible_to_agent=visible,
                coverage_pct=coverage,
                sample=[
                    CatalogProductOut(name=p.name, url=p.url, price=p.price)
                    for p in catalog_scan.products[:10]
                ],
            )
    except Exception:
        logger.exception("Catalog scan failed for %s", url_str)

    # Checklist Checks:
    parsed_url = urlparse(url_str)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # (a) /llms.txt check — existence is not enough, it must carry the catalog
    llms_txt_url = urljoin(base_url, "/llms.txt")
    llms_pass = False
    llms_evidence = ""
    try:
        async with httpx.AsyncClient(timeout=4.0, headers=_CRAWLER_HEADERS) as client:
            resp = await safe_get(client, llms_txt_url)
            if resp.status_code == 200 and len(resp.text.strip()) > 10:
                llms_pass, llms_evidence = assess_llms_txt(resp.text)
            else:
                llms_evidence = f"Failed: status {resp.status_code} or file is empty"
    except Exception as e:
        llms_evidence = f"Failed to fetch: {type(e).__name__}"

    # (b) product content check
    prod_pass = False
    prod_evidence = ""
    if analyzer.product_tokens_found:
        prod_pass = True
        prod_evidence = f"Found product indicator tokens: {', '.join(analyzer.product_tokens_found[:3])}"
    else:
        prod_evidence = "No product pricing tokens or checkout keywords found in raw HTML"

    # (c) schema.org Product check
    schema_pass = analyzer.has_schema_product
    schema_evidence = (
        "Found schema.org Product markup (itemtype or JSON-LD type)"
        if schema_pass
        else "No schema.org Product itemtype or ld+json type detected"
    )

    # (d) robots.txt UA check
    robots_url = urljoin(base_url, "/robots.txt")
    robots_pass = True
    robots_evidence = "robots.txt does not block known agent user-agents on this path"
    try:
        async with httpx.AsyncClient(timeout=4.0, headers=_CRAWLER_HEADERS) as client:
            resp = await safe_get(client, robots_url)
            if resp.status_code == 200:
                robots_pass, robots_evidence = parse_robots_txt(resp.text, parsed_url.path)
            elif resp.status_code == 404:
                robots_evidence = "robots.txt not found (assumed allowed)"
            else:
                robots_evidence = f"robots.txt returned status {resp.status_code} (assumed allowed)"
    except Exception as e:
        robots_evidence = f"Failed to check robots.txt: {type(e).__name__} (assumed allowed)"

    full_llms_txt = generate_llms_txt(url_str, analyzer.page_title, markdown, catalog_scan)
    llms_preview, llms_truncated = make_llms_preview(full_llms_txt)

    return AnalyzeResponse(
        url=url_str,
        total_bytes=total_bytes,
        script_ratio=script_ratio,
        extractable_text_pct=extractable_text_pct,
        raw_html=html_content[:15000],  # cap return snippet size for dashboard view
        markdown=markdown,
        generated_llms_txt=llms_preview,
        llms_txt_truncated=llms_truncated,
        catalog=catalog_info,
        checklist=Checklist(
            llms_txt=ChecklistItem(pass_status=llms_pass, evidence=llms_evidence),
            product_content=ChecklistItem(pass_status=prod_pass, evidence=prod_evidence),
            schema_org=ChecklistItem(pass_status=schema_pass, evidence=schema_evidence),
            robots_txt=ChecklistItem(pass_status=robots_pass, evidence=robots_evidence),
        ),
    )
