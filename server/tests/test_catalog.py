"""Tests for the catalog reality scanner (ported from Orkestra)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.catalog import (
    CatalogProduct,
    CatalogSource,
    count_visible_products,
    filter_product_urls,
    normalize_domain,
    normalize_product_name,
    parse_money_string,
    parse_shopify_products,
    parse_sitemap_urls,
    scan_catalog,
)


def test_parse_money_string_locales():
    assert parse_money_string("1.299,90") == 1299.90
    assert parse_money_string("299,90") == 299.90
    assert parse_money_string("1,299.90") == 1299.90
    assert parse_money_string("29.99") == 29.99
    assert parse_money_string("1.299.000") == 1299000.0
    assert parse_money_string("garbage") is None


def test_normalize_domain_strips_scheme_www_and_path():
    assert normalize_domain("https://www.example-store.com/products/x") == "example-store.com"
    assert normalize_domain("Books.ToScrape.com") == "books.toscrape.com"


def test_normalize_product_name_closes_parens_and_spaces():
    assert normalize_product_name("Alpine  Tent (2P") == "Alpine Tent (2P)"


def test_parse_shopify_products_picks_lowest_variant_price():
    raw = [
        {
            "title": "Demo Mousepad XL",
            "handle": "demo-mousepad-xl",
            "variants": [{"price": "449.00"}, {"price": "399.00"}],
        },
        {"title": "", "handle": "ignored-empty-title", "variants": []},
    ]
    entries = parse_shopify_products(raw, "example-store.com")
    assert len(entries) == 1
    assert entries[0].name == "Demo Mousepad XL"
    assert entries[0].price == 399.00
    assert entries[0].url == "https://example-store.com/products/demo-mousepad-xl"


def test_sitemap_parsing_and_product_filter():
    xml = (
        '<?xml version="1.0"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://shop.example/products/tent</loc></url>"
        "<url><loc>https://shop.example/pages/about</loc></url>"
        "<url><loc>https://shop.example/urun/canta</loc></url>"
        "</urlset>"
    )
    urls = parse_sitemap_urls(xml)
    assert len(urls) == 3
    assert filter_product_urls(urls) == [
        "https://shop.example/products/tent",
        "https://shop.example/urun/canta",
    ]


def test_count_visible_products_whitespace_insensitive():
    products = [
        CatalogProduct(name="Alpine Tent 2P", url="u1"),
        CatalogProduct(name="Trail Backpack 40L", url="u2"),
        CatalogProduct(name="Hidden Product Never Rendered", url="u3"),
    ]
    agent_text = "## Products\n- Alpine\n  Tent 2P — $349\n- trail backpack 40l"
    assert count_visible_products(products, agent_text) == 2


@pytest.mark.asyncio
async def test_scan_catalog_products_json_paginated():
    page1 = MagicMock(status_code=200, headers={"content-type": "application/json"})
    page1.json.return_value = {
        "products": [
            {"title": "Demo Keycap Set", "handle": "keycaps", "variants": [{"price": "199.00"}]}
        ]
    }

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=page1)):
        result = await scan_catalog("https://example-store.com")

    assert result.found
    assert result.source == CatalogSource.PRODUCTS_JSON
    assert result.total_count == 1
    assert result.products[0].name == "Demo Keycap Set"


@pytest.mark.asyncio
async def test_scan_catalog_unreachable_site_is_fail_open():
    import httpx

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=httpx.ConnectError("boom"))):
        result = await scan_catalog("https://no-such-store.example")

    assert not result.found
    assert result.source == CatalogSource.NONE
    assert result.total_count == 0
