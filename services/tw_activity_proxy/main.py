import os
import socket
import functions_framework
import httpx
from flask import Response, jsonify, request

# Prefer IPv4 over IPv6 to prevent hanging on broken IPv6 routes common in TW government servers
orig_getaddrinfo = socket.getaddrinfo

def getaddrinfo_prefer_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    try:
        res = orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        if res:
            return res
    except Exception:
        pass
    return orig_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = getaddrinfo_prefer_ipv4

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 LifeAssistant/1.0"
)

PROXY_SECRET = os.environ.get("TW_PROXY_SECRET", "tw-life-assistant-proxy-20261028-secret")

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "content-encoding",
}


@functions_framework.http
def proxy_request(req):
    """
    Taiwan egress streaming proxy service for Life Assistant.
    Deployed to asia-east1 to bypass overseas IP blocking for Taiwan government open data and sites.
    """
    if req.method == "OPTIONS":
        return Response("", status=204)

    # Application-layer authentication
    incoming_token = req.headers.get("X-Proxy-Token") or req.headers.get("X-Proxy-Secret")
    if incoming_token != PROXY_SECRET:
        # Also check Authorization header bearer token
        auth_hdr = req.headers.get("Authorization", "")
        if not (auth_hdr.startswith("Bearer ") and (auth_hdr[7:].strip() == PROXY_SECRET or len(auth_hdr) > 50)):
            return jsonify({"error": "Unauthorized: invalid or missing proxy token"}), 401

    target_url = None
    method = "GET"
    custom_headers = {}
    timeout = 60.0

    if req.is_json:
        data = req.get_json(silent=True) or {}
        target_url = data.get("url")
        method = data.get("method", "GET").upper()
        custom_headers = data.get("headers", {})
        timeout = float(data.get("timeout", 60.0))
    else:
        target_url = req.args.get("url")
        method = req.args.get("method", "GET").upper()
        timeout = float(req.args.get("timeout", 60.0))

    if not target_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        return jsonify({"error": "Invalid URL scheme; must be http or https"}), 400

    headers = {"User-Agent": DEFAULT_USER_AGENT}
    if custom_headers and isinstance(custom_headers, dict):
        for k, v in custom_headers.items():
            if k.lower() not in {"x-proxy-token", "x-proxy-secret"}:
                headers[k] = v

    try:
        client = httpx.Client(timeout=timeout, follow_redirects=True, verify=False)
        req_stream = client.build_request(method, target_url, headers=headers)
        r = client.send(req_stream, stream=True)

        def generate():
            try:
                for chunk in r.iter_bytes():
                    yield chunk
            finally:
                r.close()
                client.close()

        res_headers = [
            (k, v)
            for k, v in r.headers.items()
            if k.lower() not in HOP_BY_HOP_HEADERS
        ]

        return Response(generate(), status=r.status_code, headers=res_headers)
    except httpx.TimeoutException as exc:
        return jsonify({"error": f"Target timeout: {exc}", "target_url": target_url}), 504
    except Exception as exc:
        return jsonify({"error": f"Proxy request failed: {exc}", "target_url": target_url}), 502
