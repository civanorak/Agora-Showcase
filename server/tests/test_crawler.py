from unittest.mock import MagicMock, patch
import pytest

from app.crawler import (
    HTMLContentAnalyzer,
    HTMLToMarkdown,
    assess_llms_txt,
    generate_llms_txt,
    make_llms_preview,
)


def test_assess_llms_txt_with_priced_catalog_passes():
    text = (
        "# Demo Store\n\n## Products\n"
        "- Wireless Headphones Pro: ANC over-ear. Price: $299.\n"
        "- Leather Wallet Slim — Price: 449 TL\n"
    )
    has_catalog, evidence = assess_llms_txt(text)
    assert has_catalog is True
    assert "2 priced product lines" in evidence


def test_assess_llms_txt_instructions_only_fails():
    """Shopify's auto-generated llms.txt mentions 'products' and 'catalog'
    but lists zero priced items — agents get buying instructions, not the
    merchant's catalog. That must NOT count as catalog content."""
    text = (
        "# Agent Instructions — Demo Esports\n\n"
        "Use `search_catalog` to find products matching the buyer's intent.\n"
        "- Cross-store catalog search and price/discount discovery\n"
        "- Buyer-approved checkout via Shop Pay\n"
    )
    has_catalog, evidence = assess_llms_txt(text)
    assert has_catalog is False
    assert "no priced product lines" in evidence


def test_assess_llms_txt_html_soft404_fails():
    has_catalog, evidence = assess_llms_txt("<!DOCTYPE html><html><body>404</body></html>")
    assert has_catalog is False
    assert "HTML page" in evidence


def test_generate_llms_txt_from_crawled_page():
    """The generated llms.txt must be a ready-to-host file: title header,
    source URL, and the product lines extracted from the page."""
    html = (
        "<html><head><title>Demo Outdoor Gear</title>"
        "<script>var x = 1;</script></head>"
        "<body>"
        "<h1>Demo Outdoor Gear</h1>"
        "<h2>Products</h2>"
        "<ul>"
        "<li>Alpine Tent 2P — Price: $349</li>"
        "<li>Trail Backpack 40L — Price: $129</li>"
        "</ul>"
        "<p>Free shipping on orders over $100.</p>"
        "</body></html>"
    )
    analyzer = HTMLContentAnalyzer()
    analyzer.feed(html)
    md_parser = HTMLToMarkdown()
    md_parser.feed(html)

    result = generate_llms_txt(
        url="https://demo.example/shop",
        page_title=analyzer.page_title,
        markdown=md_parser.get_markdown(),
    )

    assert result.startswith("# Demo Outdoor Gear")
    assert "https://demo.example/shop" in result
    assert "Alpine Tent 2P" in result
    assert "$349" in result
    # No script junk leaks into the generated file
    assert "var x" not in result


def test_markdown_output_has_no_whitespace_junk():
    """Indented real-world HTML must not leave space-only lines or blank-line
    runs in the markdown — that junk wastes agent tokens."""
    html = (
        "<html><body>\n"
        "    <div>\n"
        "        <div>\n            \n        </div>\n"
        "        <p>Alpine Tent 2P</p>\n"
        "        <ul>\n"
        "            <li>\n                <a href='/tents'>\n\n    All Tents\n\n</a>\n            </li>\n"
        "        </ul>\n"
        "    </div>\n"
        "</body></html>"
    )
    md_parser = HTMLToMarkdown()
    md_parser.feed(html)
    md = md_parser.get_markdown()

    assert "Alpine Tent 2P" in md
    # Link text collapses to a single-line markdown link on the list marker line
    assert "- [All Tents](/tents)" in md
    assert "\n\n\n" not in md
    for line in md.split("\n"):
        assert line == line.rstrip(), f"trailing whitespace in line: {line!r}"
        assert not (line and not line.strip()), "space-only line survived"


def test_generate_llms_txt_falls_back_to_host_when_no_title():
    result = generate_llms_txt(url="https://shop.example", page_title="", markdown="Some content")
    assert result.startswith("# shop.example")


def test_generate_llms_txt_prefers_structured_catalog():
    """When the catalog scan found real products, the Products section comes
    from structured entries (name/price/URL), not from page markdown."""
    from app.catalog import CatalogProduct, CatalogScan, CatalogSource

    catalog = CatalogScan(
        products=[
            CatalogProduct(name="Demo Mousepad XL", url="https://w.example/products/pad", price=399.0),
            CatalogProduct(name="Demo Keycap Set", url="https://w.example/products/keys", price=None),
        ],
        total_count=57,
        source=CatalogSource.PRODUCTS_JSON,
    )
    result = generate_llms_txt(
        url="https://w.example",
        page_title="Demo Esports",
        markdown="nav nav nav footer junk",
        catalog=catalog,
    )

    assert "## Products (57)" in result
    assert "- [Demo Mousepad XL](https://w.example/products/pad) — Price: 399" in result
    assert "- [Demo Keycap Set](https://w.example/products/keys)" in result
    assert "…and 55 more products" in result
    # Page markdown junk must not leak into the catalog-backed file
    assert "nav nav nav" not in result


@pytest.mark.asyncio
async def test_analyze_url_endpoint(client):
    mock_html = (
        "<html>"
        "<head><style>body { color: red; }</style></head>"
        "<body>"
        "<h1>Wireless Headphones Pro</h1>"
        "<p>Price: $299</p>"
        "<div itemtype='http://schema.org/Product'>Product Item</div>"
        "</body>"
        "</html>"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": str(len(mock_html))}

    async def mock_aiter_bytes():
        yield mock_html.encode("utf-8")

    mock_response.aiter_bytes = mock_aiter_bytes

    class MockStreamContext:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_llms_resp = MagicMock()
    mock_llms_resp.status_code = 200
    mock_llms_resp.text = (
        "# Mock Store\n- Item A — Price: $10\n- Item B — Price: $20\n"
    )
    mock_llms_resp.content = mock_llms_resp.text.encode()

    mock_robots_resp = MagicMock()
    mock_robots_resp.status_code = 200
    mock_robots_resp.text = "User-agent: *\nDisallow: /private"

    from unittest.mock import AsyncMock

    with patch("httpx.AsyncClient.stream", return_value=MockStreamContext()), patch(
        "app.ssrf._resolve", new=AsyncMock(return_value=["93.184.216.34"])
    ), patch("httpx.AsyncClient.get") as mock_get:

        def side_effect(url, **kwargs):
            if "llms.txt" in url:
                return mock_llms_resp
            if "robots.txt" in url:
                return mock_robots_resp
            return MagicMock(status_code=404)

        mock_get.side_effect = side_effect

        resp = await client.post(
            "/report/analyze", json={"url": "http://localhost:8000/products/laptop"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "http://localhost:8000/products/laptop"
        assert data["total_bytes"] == len(mock_html)
        assert data["script_ratio"] > 0.0  # style tags should count as script_ratio
        assert data["extractable_text_pct"] > 0.0
        assert "Wireless Headphones Pro" in data["raw_html"]
        assert "Wireless Headphones Pro" in data["markdown"]

        checklist = data["checklist"]
        assert checklist["llms_txt"]["pass_status"] is True
        assert checklist["product_content"]["pass_status"] is True
        assert checklist["schema_org"]["pass_status"] is True
        assert checklist["robots_txt"]["pass_status"] is True
        # No /products.json or sitemap in this mock → no catalog block, audit still succeeds
        assert data["catalog"] is None


@pytest.mark.asyncio
async def test_analyze_url_rejects_internal_target(client):
    """The endpoint must refuse to fetch loopback/private targets (SSRF guard)."""
    resp = await client.post(
        "/report/analyze", json={"url": "http://127.0.0.1:8000/admin"}
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "refused"
    assert "127.0.0.1" in detail["message"]


@pytest.mark.asyncio
async def test_analyze_url_includes_catalog_reality_diff(client):
    """When the store exposes a structured catalog, the response carries the
    catalog-vs-agent coverage diff and the llms.txt is catalog-backed."""
    from unittest.mock import AsyncMock
    from app.catalog import CatalogProduct, CatalogScan, CatalogSource

    mock_html = "<html><head><title>Demo Store</title></head><body><h1>Demo Mousepad XL</h1></body></html>"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": str(len(mock_html))}

    async def mock_aiter_bytes():
        yield mock_html.encode("utf-8")

    mock_response.aiter_bytes = mock_aiter_bytes

    class MockStreamContext:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    scan = CatalogScan(
        products=[
            CatalogProduct(name="Demo Mousepad XL", url="https://w.example/products/pad", price=399.0),
            CatalogProduct(name="Invisible Keyboard", url="https://w.example/products/kb", price=899.0),
        ],
        total_count=2,
        source=CatalogSource.PRODUCTS_JSON,
    )

    with patch("httpx.AsyncClient.stream", return_value=MockStreamContext()), patch(
        "app.ssrf._resolve", new=AsyncMock(return_value=["93.184.216.34"])
    ), patch(
        "httpx.AsyncClient.get", new=AsyncMock(return_value=MagicMock(status_code=404))
    ), patch("app.crawler.scan_catalog", new=AsyncMock(return_value=scan)):
        resp = await client.post("/report/analyze", json={"url": "https://w.example/"})

    assert resp.status_code == 200
    data = resp.json()
    catalog = data["catalog"]
    assert catalog["source"] == "products_json"
    assert catalog["total_count"] == 2
    # Only the mousepad appears in the crawled HTML — the keyboard is invisible to agents
    assert catalog["visible_to_agent"] == 1
    assert catalog["coverage_pct"] == 50.0
    assert len(catalog["sample"]) == 2
    assert "## Products (2)" in data["generated_llms_txt"]
    # Two products fit inside the preview window — nothing is gated
    assert data["llms_txt_truncated"] is False


def _catalog_llms_txt(product_count: int) -> str:
    header = (
        "# Demo Store\n\n"
        "> Machine-readable storefront summary generated by AGORA.\n"
        "> Source: https://demo.example\n\n"
        f"## Products ({product_count})\n\n"
    )
    lines = "\n".join(
        f"- [Product {i}](https://demo.example/products/p{i}) — Price: {100 + i}"
        for i in range(product_count)
    )
    return header + lines + "\n"


def test_make_llms_preview_gates_large_catalog():
    """The public audit response must not hand out the full deliverable:
    only the first 10 product lines survive, the rest is replaced by a
    gate line pointing at the install package."""
    preview, truncated = make_llms_preview(_catalog_llms_txt(25))

    assert truncated is True
    assert preview.count("- [") == 10
    assert "- [Product 9]" in preview
    assert "- [Product 10]" not in preview
    assert "15+ more product lines" in preview
    assert "install package" in preview
    # Header stays intact so the preview still reads as a real llms.txt
    assert preview.startswith("# Demo Store")
    assert "## Products (25)" in preview


def test_make_llms_preview_leaves_small_catalog_untouched():
    full = _catalog_llms_txt(5)
    preview, truncated = make_llms_preview(full)
    assert truncated is False
    assert preview == full


def test_make_llms_preview_truncates_long_content_file():
    """Non-catalog files (markdown-backed) are gated by size instead of
    product-line count."""
    full = (
        "# Content Site\n\n"
        "> Machine-readable storefront summary generated by AGORA.\n"
        "> Source: https://content.example\n\n"
        + ("Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n" * 40)
    )
    preview, truncated = make_llms_preview(full)
    assert truncated is True
    assert len(preview) < len(full)
    assert "install package" in preview


# ── Fetch resilience & friendly errors ────────────────────────────────────────

from contextlib import asynccontextmanager  # noqa: E402

import httpx  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.crawler import _fetch_page  # noqa: E402
from app.ssrf import SSRFError  # noqa: E402


def _resp(status, headers=None, body=b"<html>ok</html>"):
    r = MagicMock()
    r.status_code = status
    r.headers = headers or {}

    async def _aiter():
        yield body

    r.aiter_bytes = _aiter
    return r


def _patch_stream(*, responses=None, raises=None):
    """Return an async-context-manager stand-in for safe_stream that yields the
    given responses in order (last repeats) or raises `raises` on entry."""
    state = {"n": 0}

    @asynccontextmanager
    async def _ss(client, method, url, **kwargs):
        if raises is not None:
            raise raises
        i = min(state["n"], len(responses) - 1)
        state["n"] += 1
        yield responses[i]

    return _ss, state


class TestFetchResilience:
    async def test_blocked_then_retry_succeeds(self):
        ss, state = _patch_stream(responses=[_resp(403), _resp(200)])
        with patch("app.crawler.safe_stream", ss):
            body = await _fetch_page("https://blocked.example/")
        assert body == b"<html>ok</html>"
        assert state["n"] == 2  # first blocked, retried with plain UA

    async def test_persistent_block_is_friendly(self):
        ss, _ = _patch_stream(responses=[_resp(403), _resp(403)])
        with patch("app.crawler.safe_stream", ss):
            with pytest.raises(HTTPException) as exc:
                await _fetch_page("https://blocked.example/")
        assert exc.value.detail["code"] == "blocked"
        assert exc.value.detail["status"] == 403

    async def test_404_is_not_retried_and_tagged(self):
        ss, state = _patch_stream(responses=[_resp(404)])
        with patch("app.crawler.safe_stream", ss):
            with pytest.raises(HTTPException) as exc:
                await _fetch_page("https://missing.example/x")
        assert exc.value.detail["code"] == "not_found"
        assert state["n"] == 1  # 404 is a real answer — no retry

    async def test_oversize_by_content_length_is_rejected(self):
        big = _resp(200, headers={"Content-Length": str(3 * 1024 * 1024)})
        ss, _ = _patch_stream(responses=[big])
        with patch("app.crawler.safe_stream", ss):
            with pytest.raises(HTTPException) as exc:
                await _fetch_page("https://huge.example/")
        assert exc.value.detail["code"] == "too_large"

    async def test_ssrf_refusal_is_friendly(self):
        ss, _ = _patch_stream(raises=SSRFError("URL host is a non-public address: 127.0.0.1"))
        with patch("app.crawler.safe_stream", ss):
            with pytest.raises(HTTPException) as exc:
                await _fetch_page("http://127.0.0.1/")
        assert exc.value.detail["code"] == "refused"

    async def test_timeout_is_unreachable(self):
        ss, _ = _patch_stream(raises=httpx.ConnectTimeout("timed out"))
        with patch("app.crawler.safe_stream", ss):
            with pytest.raises(HTTPException) as exc:
                await _fetch_page("https://slow.example/")
        assert exc.value.detail["code"] == "unreachable"
