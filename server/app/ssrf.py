"""SSRF guard for user-supplied audit URLs.

The public `/report/analyze` endpoint fetches arbitrary merchant URLs. Without a
guard an attacker could point it at internal infrastructure (cloud metadata
endpoints, localhost admin panels, private RFC1918 ranges). This module resolves
the hostname and rejects any URL that maps to a non-public IP address.

Design notes:
- We resolve DNS ourselves and inspect *every* returned address, defeating
  DNS-rebinding-at-resolution and A/AAAA split tricks.
- Fail-closed: resolution failure or an ambiguous address raises SSRFError.
- Scheme is restricted to http/https by the caller before this runs, but we
  re-check defensively.
"""

import asyncio
import ipaddress
import socket
from contextlib import asynccontextmanager
from urllib.parse import urljoin, urlparse

_ALLOWED_SCHEMES = ("http", "https")

# A validated URL is worthless if the server then follows an attacker-controlled
# redirect to an internal address. We follow redirects ourselves, re-validating
# every hop, and cap the chain so a redirect loop cannot hang the worker.
MAX_REDIRECTS = 5
_REDIRECT_STATUS = frozenset((301, 302, 303, 307, 308))


class SSRFError(ValueError):
    """Raised when a URL resolves to a disallowed (non-public) address."""


def _is_public_ip(ip: str) -> bool:
    """True only for globally routable unicast addresses."""
    addr = ipaddress.ip_address(ip)
    if any(
        (
            addr.is_private,
            addr.is_loopback,
            addr.is_link_local,
            addr.is_multicast,
            addr.is_reserved,
            addr.is_unspecified,
        )
    ):
        return False
    # IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) must be judged on the mapped v4.
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return _is_public_ip(str(addr.ipv4_mapped))
    return addr.is_global


async def _resolve(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    return [info[4][0] for info in infos]


async def validate_public_url(url: str) -> None:
    """Raise SSRFError if `url` does not resolve to a public IP address.

    Returns None on success so callers can `await validate_public_url(url)`
    as a guard before fetching.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise SSRFError(f"Disallowed URL scheme: {parsed.scheme or '(none)'}")

    host = parsed.hostname
    if not host:
        raise SSRFError("URL has no host")

    # A bare IP literal in the URL is validated directly.
    try:
        ipaddress.ip_address(host)
        literal = True
    except ValueError:
        literal = False

    if literal:
        if not _is_public_ip(host):
            raise SSRFError(f"URL host is a non-public address: {host}")
        return

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addresses = await _resolve(host, port)
    except socket.gaierror as exc:
        raise SSRFError(f"Could not resolve host: {host}") from exc

    if not addresses:
        raise SSRFError(f"Host resolved to no addresses: {host}")

    for ip in addresses:
        if not _is_public_ip(ip):
            raise SSRFError(f"Host {host} resolves to non-public address {ip}")


def _redirect_target(response, current_url: str) -> str | None:
    """Return the next absolute URL if `response` is a redirect, else None."""
    if response.status_code not in _REDIRECT_STATUS:
        return None
    location = response.headers.get("location")
    if not location:
        return None
    return urljoin(current_url, location)


async def safe_get(client, url: str, **kwargs):
    """httpx GET that SSRF-validates the initial URL and every redirect hop.

    Redirect following is done manually (never `follow_redirects=True`) so an
    attacker cannot use a public URL that 302-redirects to an internal target
    to bypass `validate_public_url`. Raises SSRFError on any disallowed hop or
    when the redirect chain exceeds MAX_REDIRECTS.
    """
    kwargs["follow_redirects"] = False
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        await validate_public_url(current)
        response = await client.get(current, **kwargs)
        nxt = _redirect_target(response, current)
        if nxt is None:
            return response
        current = nxt
    raise SSRFError(f"Exceeded {MAX_REDIRECTS} redirects starting from {url}")


@asynccontextmanager
async def safe_stream(client, method: str, url: str, **kwargs):
    """Streaming counterpart to `safe_get` with the same per-hop SSRF guard.

    Yields the final (non-redirect) streamed response inside an async context so
    the caller can read it with a byte cap. Every hop — including redirects — is
    validated before a connection is opened.
    """
    kwargs["follow_redirects"] = False
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        await validate_public_url(current)
        stream_cm = client.stream(method, current, **kwargs)
        response = await stream_cm.__aenter__()
        nxt = _redirect_target(response, current)
        if nxt is None:
            try:
                yield response
            finally:
                await stream_cm.__aexit__(None, None, None)
            return
        await stream_cm.__aexit__(None, None, None)
        current = nxt
    raise SSRFError(f"Exceeded {MAX_REDIRECTS} redirects starting from {url}")
