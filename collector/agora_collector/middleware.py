"""AGORA Collector — ASGI middleware for agent traffic detection."""

import asyncio
import logging
from typing import Any, Callable

import httpx

logger = logging.getLogger("agora.collector")


class AGORACollector:
    """
    ASGI middleware that captures HTTP requests and sends them to AGORA ingest.

    Usage:
        from agora_collector import AGORACollector

        app = YourASGIApp()
        app = AGORACollector(app, api_url="https://your-agora.com", api_key="your-key")
    """

    def __init__(
        self,
        app: Any,
        api_url: str,
        api_key: str,
        site_id: str,
        timeout_ms: int = 2000,
        paths_to_ignore: list[str] | None = None,
    ):
        self.app = app
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.site_id = site_id
        self.timeout_ms = timeout_ms
        self.paths_to_ignore = paths_to_ignore or [
            "/static/",
            "/assets/",
            "/favicon.ico",
        ]
        self._client: httpx.AsyncClient | None = None
        self._buffer: list[dict] = []
        self._flush_interval = 5.0  # seconds
        self._flush_task: asyncio.Task | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_ms / 1000)
            )
        return self._client

    def _should_capture(self, path: str) -> bool:
        return not any(path.startswith(ignore) for ignore in self.paths_to_ignore)

    def _extract_event(self, scope: dict, request_headers: dict) -> dict:
        """Build event payload from ASGI scope."""
        # Extract headers as dict
        headers = {}
        for key, value in scope.get("headers", []):
            headers[key.decode()] = value.decode()

        return {
            "method": scope.get("method", "GET"),
            "path": scope.get("path", "/"),
            "status": 200,  # updated from http.response.start in __call__
            "user_agent": headers.get("user-agent", ""),
            "ip": headers.get("x-forwarded-for", headers.get("x-real-ip", "")),
            "headers": {
                k: v
                for k, v in headers.items()
                if k.lower() in ("accept", "accept-language", "accept-encoding", "host")
            },
            "site_id": self.site_id,
            "beacon_seen": False,
        }

    async def _send_event(self, event: dict) -> bool:
        """Send event to AGORA ingest API. Returns True on success."""
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.api_url}/ingest",
                json=event,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            return resp.status_code == 200
        except Exception:
            logger.debug("Failed to send event to AGORA", exc_info=True)
            return False

    async def _flush_buffer(self) -> None:
        """Send buffered events in batch."""
        if not self._buffer:
            return
        events = self._buffer[:]
        self._buffer.clear()
        for event in events:
            await self._send_event(event)

    async def _periodic_flush(self) -> None:
        """Background task to flush buffer periodically."""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_buffer()

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if not self._should_capture(path):
            await self.app(scope, receive, send)
            return

        event = self._extract_event(scope, {})

        # Start periodic flush on first request
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

        # Capture the real response status without buffering the body
        async def send_wrapper(message: dict) -> None:
            if message.get("type") == "http.response.start":
                event["status"] = message.get("status", 200)
            await send(message)

        try:
            # Continue to upstream app — our failure must NEVER block merchant's store
            await self.app(scope, receive, send_wrapper)
        finally:
            # Fire-and-forget after the response: real status attached, never blocks upstream
            asyncio.create_task(self._send_event(event))

    async def close(self) -> None:
        """Graceful shutdown — flush remaining events."""
        if self._flush_task:
            self._flush_task.cancel()
        await self._flush_buffer()
        if self._client:
            await self._client.aclose()
