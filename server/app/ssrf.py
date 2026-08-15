"""SSRF guard for user-supplied audit URLs.

The public `/report/analyze` endpoint fetches arbitrary merchant URLs. Without a
guard an attacker could point it at internal infrastructure (cloud metadata
endpoints, localhost admin panels, private RFC1918 ranges). This module resolves
the hostname and rejects any URL that maps to a non-public IP address.

Design notes:
- We resolve DNS ourselves and inspect *every* returned address, rejecting
  A/AAAA split tricks where one record is public and another internal.
- We then *pin* the connection to a single validated IP and hand httpx that IP
  literal (with the original Host header + TLS SNI preserved). Without pinning,
  httpx would re-resolve the hostname at connect time, and an attacker running a
  low-TTL DNS server could return a public IP for our check and a private IP for
  the real fetch — the classic DNS-rebinding TOCTOU. Pinning closes that window.
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


async def _validated_ips(host: str, port: int) -> list[str]:
    """Resolve `host` and return its addresses, raising SSRFError unless *every*
    returned address is public. Fail-closed on resolution failure."""
    try:
        addresses = await _resolve(host, port)
    except socket.gaierror as exc:
        raise SSRFError(f"Could not resolve host: {host}") from exc

    if not addresses:
        raise SSRFError(f"Host resolved to no addresses: {host}")

    for ip in addresses:
        if not _is_public_ip(ip):
            raise SSRFError(f"Host {host} resolves to non-public address {ip}")
    return addresses


def _authority(parsed) -> str:
    """host[:port] for the Host header, bracketing IPv6 and dropping userinfo."""
    host = parsed.hostname
    if host and ":" in host:  # IPv6 literal
        host = f"[{host}]"
    return f"{host}:{parsed.port}" if parsed.port else host


def _swap_host(parsed, ip: str) -> str:
    """Rebuild the URL with `ip` in place of the hostname (userinfo dropped)."""
    netloc = f"[{ip}]" if ":" in ip else ip
    if parsed.port:
        netloc += f":{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


async def validate_public_url(url: str) -> None:
    """Raise SSRFError if `url` does not resolve to a public IP address.

    Returns None on success so callers can `await validate_public_url(url)`
    as a guard before fetching. Note: this validates only — it does not pin the
    resolved IP, so a fetch that re-resolves the hostname is still exposed to DNS
    rebinding. Prefer `safe_get` / `safe_stream` / `pinned_get`, which pin.
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
    await _validated_ips(host, port)


async def _pinned_target(url: str) -> tuple[str, str, str | None]:
    """Validate `url` and pin it to one validated IP.

    Returns (request_url, host_header, sni_hostname):
      - request_url has the hostname replaced by a validated IP literal, so httpx
        connects to that exact address and cannot re-resolve to an internal one
        between our check and the connect (DNS-rebinding TOCTOU).
      - host_header is the original authority, preserved so virtual hosting works.
      - sni_hostname is the original hostname for the TLS handshake and cert
        verification, or None for plain HTTP or when the URL is already an IP
        literal (nothing to re-resolve, so no rewrite is needed).

    Raises SSRFError on any disallowed address.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise SSRFError(f"Disallowed URL scheme: {parsed.scheme or '(none)'}")

    host = parsed.hostname
    if not host:
        raise SSRFError("URL has no host")

    try:
        ipaddress.ip_address(host)
        literal = True
    except ValueError:
        literal = False

    if literal:
        if not _is_public_ip(host):
            raise SSRFError(f"URL host is a non-public address: {host}")
        # Already an IP literal — no hostname for httpx to re-resolve.
        return url, _authority(parsed), None

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = await _validated_ips(host, port)
    pinned_ip = addresses[0]
    sni = host if parsed.scheme == "https" else None
    return _swap_host(parsed, pinned_ip), _authority(parsed), sni


def _apply_pin(kwargs: dict, host_header: str, sni: str | None) -> dict:
    """Merge the pinned Host header and SNI override into httpx call kwargs."""
    headers = dict(kwargs.get("headers") or {})
    headers["Host"] = host_header
    merged = {**kwargs, "headers": headers, "follow_redirects": False}
    if sni is not None:
        ext = dict(merged.get("extensions") or {})
        ext.setdefault("sni_hostname", sni)
        merged["extensions"] = ext
    return merged


async def pinned_get(client, url: str, **kwargs):
    """Single httpx GET pinned to a validated IP (no redirect following).

    SSRF-validates `url`, then connects to the resolved IP with the original Host
    header and TLS SNI. Redirects are NOT followed — the raw response (including
    any 3xx) is returned so callers that treat a redirect as "no data" keep that
    behaviour. Raises SSRFError if the URL resolves to a non-public address.
    """
    request_url, host_header, sni = await _pinned_target(url)
    return await client.get(request_url, **_apply_pin(kwargs, host_header, sni))


def _redirect_target(response, current_url: str) -> str | None:
    """Return the next absolute URL if `response` is a redirect, else None."""
    if response.status_code not in _REDIRECT_STATUS:
        return None
    location = response.headers.get("location")
    if not location:
        return None
    return urljoin(current_url, location)


async def safe_get(client, url: str, **kwargs):
    """httpx GET that SSRF-validates and IP-pins the initial URL and every
    redirect hop.

    Redirect following is done manually (never `follow_redirects=True`) so an
    attacker cannot use a public URL that 302-redirects to an internal target to
    bypass the guard. Each hop is validated *and pinned* to a resolved IP before
    the request, closing both the redirect-bypass and DNS-rebinding holes. Raises
    SSRFError on any disallowed hop or when the chain exceeds MAX_REDIRECTS.
    """
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        response = await pinned_get(client, current, **kwargs)
        # Location is relative to the real host, not the pinned IP literal.
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
    validated and IP-pinned before a connection is opened.
    """
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        request_url, host_header, sni = await _pinned_target(current)
        call_kwargs = _apply_pin(kwargs, host_header, sni)
        stream_cm = client.stream(method, request_url, **call_kwargs)
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
