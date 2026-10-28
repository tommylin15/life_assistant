"""
Taiwan Activity Request Router & Adaptive Routing Cache.
Enables transparent routing between direct connections and asia-east1 Cloud Function Proxy,
with auto-learning of overseas IP blocked sites to avoid repeated timeout delays.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

DEFAULT_PROXY_URL = os.environ.get(
    "TW_PROXY_URL",
    "https://tw-activity-proxy-2oo7qbkd5q-de.a.run.app",
)

METADATA_IDENTITY_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
)

DEFAULT_PROXY_SECRET = os.environ.get(
    "TW_PROXY_SECRET",
    "tw-life-assistant-proxy-20261028-secret",
)

LOCAL_CACHE_PATH = Path("config/source_routing_cache.json")
DRIVE_CACHE_PATH = Path(
    "/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟/台灣活動探索｜來源路由控制.json"
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 LifeAssistant/1.0"
)

SOCIAL_CRAWLER_USER_AGENT = (
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
)

SOCIAL_OPENGRAPH_DOMAINS = {
    "threads.com",
    "www.threads.com",
    "threads.net",
    "www.threads.net",
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "instagram.com",
    "www.instagram.com",
}


class TWRequestRouter:
    def __init__(
        self,
        cache_path: Path = LOCAL_CACHE_PATH,
        drive_sync_path: Optional[Path] = DRIVE_CACHE_PATH,
        proxy_url: str = DEFAULT_PROXY_URL,
    ):
        self.cache_path = cache_path
        self.drive_sync_path = drive_sync_path
        self.proxy_url = proxy_url
        self.routes: Dict[str, Dict[str, Any]] = {}
        self._cached_token: Optional[str] = None
        self.load_cache()

    def load_cache(self) -> None:
        path_to_read = None
        if self.cache_path.exists():
            path_to_read = self.cache_path
        elif self.drive_sync_path and self.drive_sync_path.exists():
            path_to_read = self.drive_sync_path

        if path_to_read:
            try:
                with open(path_to_read, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.routes = data.get("routes", {})
            except Exception as e:
                logger.warning(f"Failed to load routing cache from {path_to_read}: {e}")
                self.routes = {}
        else:
            self.routes = {}

    def save_cache(self) -> None:
        data = {
            "version": "1.0",
            "routes": self.routes,
        }
        # Save local
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save local routing cache to {self.cache_path}: {e}")

        # Save to Drive if available
        if self.drive_sync_path and self.drive_sync_path.parent.exists():
            try:
                with open(self.drive_sync_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to sync routing cache to Drive: {e}")

    def is_proxy_required(self, domain: str) -> bool:
        norm_domain = domain.lower().strip()
        route_info = self.routes.get(norm_domain)
        if route_info and route_info.get("route") == "TW_PROXY":
            return True
        return False

    def mark_route(self, domain: str, route: str, reason: str, note: str = "") -> None:
        norm_domain = domain.lower().strip()
        from datetime import datetime, timezone, timedelta
        tpe_now = datetime.now(timezone(timedelta(hours=8))).isoformat()

        self.routes[norm_domain] = {
            "route": route,
            "reason": reason,
            "marked_at": tpe_now,
            "note": note,
        }
        self.save_cache()
        logger.info(f"[ROUTER] Updated route for {norm_domain}: route={route}, reason={reason}")

    def get_id_token(self, audience: Optional[str] = None) -> Optional[str]:
        aud = audience or self.proxy_url
        try:
            resp = requests.get(
                METADATA_IDENTITY_URL,
                params={"audience": aud, "format": "full"},
                headers={"Metadata-Flavor": "Google"},
                timeout=2.5,
            )
            if resp.status_code == 200:
                self._cached_token = resp.text.strip()
                return self._cached_token
        except Exception as e:
            logger.debug(f"[ROUTER] Could not obtain metadata identity token: {e}")
        return None

    def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        direct_timeout: float = 5.0,
        allow_proxy: bool = True,
        stream: bool = False,
        **kwargs: Any,
    ) -> requests.Response:
        parsed = urlparse(url)
        domain = parsed.netloc.split(":")[0].lower()

        default_ua = (
            SOCIAL_CRAWLER_USER_AGENT
            if domain in SOCIAL_OPENGRAPH_DOMAINS
            else DEFAULT_USER_AGENT
        )
        req_headers = {"User-Agent": default_ua}
        if headers:
            req_headers.update(headers)

        # 1. Check if domain is already marked for Taiwan Proxy
        if allow_proxy and self.is_proxy_required(domain):
            logger.info(f"[ROUTER] Domain '{domain}' is cached as TW_PROXY; routing directly via Cloud Function...")
            return self._call_proxy(
                target_url=url,
                method=method,
                headers=req_headers,
                timeout=timeout,
                stream=stream,
                **kwargs,
            )

        # 2. Try direct connection with bounded timeout
        try:
            logger.debug(f"[ROUTER] Attempting direct {method} to {url} (timeout={direct_timeout}s)...")
            resp = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                timeout=direct_timeout,
                stream=stream,
                **kwargs,
            )
            # If 403 and overseas restriction suspected
            if resp.status_code == 403 and allow_proxy:
                logger.warning(f"[ROUTER] Direct request to {domain} returned 403, attempting proxy fallback...")
                proxy_resp = self._call_proxy(
                    target_url=url,
                    method=method,
                    headers=req_headers,
                    timeout=timeout,
                    stream=stream,
                    **kwargs,
                )
                if proxy_resp.status_code < 400:
                    self.mark_route(domain, "TW_PROXY", "OVERSEAS_403_BLOCKED", "Auto-learned by router")
                    return proxy_resp
            return resp
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            if not allow_proxy:
                raise

            reason = "OVERSEAS_CONNECTION_TIMEOUT" if isinstance(exc, requests.exceptions.Timeout) else "OVERSEAS_CONNECTION_ERROR"
            logger.warning(f"[ROUTER] Direct request to {domain} failed ({reason}), falling back to Taiwan Cloud Function...")
            proxy_resp = self._call_proxy(
                target_url=url,
                method=method,
                headers=req_headers,
                timeout=timeout,
                stream=stream,
                **kwargs,
            )
            if proxy_resp.status_code < 400:
                self.mark_route(domain, "TW_PROXY", reason, "Auto-learned by router")
            return proxy_resp

    def _call_proxy(
        self,
        target_url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 60.0,
        stream: bool = False,
        **kwargs: Any,
    ) -> requests.Response:
        proxy_headers = {
            "Content-Type": "application/json",
            "X-Proxy-Token": DEFAULT_PROXY_SECRET,
        }
        token = self.get_id_token(self.proxy_url)
        if token:
            proxy_headers["Authorization"] = f"Bearer {token}"

        payload = {
            "url": target_url,
            "method": method,
            "headers": headers or {},
            "timeout": timeout,
        }

        resp = requests.post(
            self.proxy_url,
            headers=proxy_headers,
            json=payload,
            timeout=timeout + 5.0,
            stream=stream,
        )
        return resp


# Singleton router instance for shared use
default_router = TWRequestRouter()


def smart_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    direct_timeout: float = 5.0,
    allow_proxy: bool = True,
    stream: bool = False,
    **kwargs: Any,
) -> requests.Response:
    return default_router.request(
        url=url,
        method=method,
        headers=headers,
        timeout=timeout,
        direct_timeout=direct_timeout,
        allow_proxy=allow_proxy,
        stream=stream,
        **kwargs,
    )
