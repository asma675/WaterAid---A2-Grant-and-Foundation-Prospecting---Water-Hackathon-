from __future__ import annotations
import asyncio
import ipaddress
import socket
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx
from .config import settings

class FetchBlocked(ValueError):
    pass

async def _assert_public_host(host: str):
    loop=asyncio.get_running_loop()
    infos=await loop.run_in_executor(None, socket.getaddrinfo, host, 443, 0, socket.SOCK_STREAM)
    for info in infos:
        ip=ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise FetchBlocked("Private or reserved network targets are blocked")

async def fetch_public_page(url: str) -> dict[str, str]:
    if not settings.live_fetch_enabled:
        raise FetchBlocked("Live fetching is disabled. Set LIVE_FETCH_ENABLED=true after reviewing source terms.")
    parsed=urlparse(url)
    if parsed.scheme not in {"http","https"} or not parsed.hostname:
        raise FetchBlocked("Only public HTTP(S) URLs are supported")
    await _assert_public_host(parsed.hostname)
    robots=f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        try:
            r=await client.get(robots, headers={"User-Agent":"GrantCurrentBot/1.0"})
            rp=RobotFileParser(); rp.set_url(robots); rp.parse(r.text.splitlines())
            if not rp.can_fetch("GrantCurrentBot/1.0", url):
                raise FetchBlocked("robots.txt disallows automated access")
        except FetchBlocked:
            raise
        except Exception:
            # Conservative: robots failure means do not crawl automatically.
            raise FetchBlocked("Could not verify robots.txt; manual review required")
        resp=await client.get(url, headers={"User-Agent":"GrantCurrentBot/1.0"})
        resp.raise_for_status()
        content=resp.content[:settings.source_max_bytes]
        return {"url": url, "content_type": resp.headers.get("content-type", ""), "text": content.decode(resp.encoding or "utf-8", errors="replace")}
