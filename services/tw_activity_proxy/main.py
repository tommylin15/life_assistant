import functions_framework
import httpx
from flask import Response, jsonify, request

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 LifeAssistant/1.0"
)

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
}


@functions_framework.http
def proxy_request(req):
    """
    Taiwan egress streaming proxy function for Life Assistant.
    Deployed to asia-east1 to bypass overseas IP blocking for Taiwan government open data and sites.
    """
    if req.method == "OPTIONS":
        return Response("", status=204)

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
        headers.update(custom_headers)

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
