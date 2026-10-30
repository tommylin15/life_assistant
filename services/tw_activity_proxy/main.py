"""Bounded private Taiwan egress for the existing Life and Janus callers.

Cloud Run Invoker IAM is the authentication boundary. Do not expose this
service publicly or rely on a caller-provided shared header as authentication.
"""
import ipaddress
import json
import os
import re
import socket
from urllib.parse import parse_qs, urlsplit

import functions_framework
import httpx
from flask import Response, jsonify

# These are explicit source hosts, not a suffix/domain wildcard. Expand only
# when an approved Life source requires it and review the resulting diff.
LIFE_HOSTS = frozenset({
    "cloud.culture.tw", "media.taiwan.net.tw", "fae.moa.gov.tw",
    "rse.ardswc.gov.tw", "event.hchcc.gov.tw",
    "eservices.taichung.gov.tw", "www.forest.gov.tw",
    "www.tyfa.org.tw", "www.hccg.gov.tw", "ccl.taitung.gov.tw",
    "culture.gov.taipei", "www.culture.ntpc.gov.tw",
    "travel.taichung.gov.tw", "www.twtainan.net",
    "event.ner.gov.tw", "www.hakka.ntpc.gov.tw",
    "www.agriculture.ntpc.gov.tw", "ntpc-farming.com",
    "kktix.cc", "eventgo.tw", "ezgo.ardswc.gov.tw",
    "www.tyfa.com.tw", "www.ardswc.gov.tw",
    "tourism.hccg.gov.tw",
})
JANUS_HOST = "mis.twse.com.tw"
ALLOWED_HOSTS = LIFE_HOSTS | {JANUS_HOST}
CHANNEL = re.compile(r"^(?:tse|otc)_[A-Za-z0-9]{3,10}\.tw$")
AGENT = "JanusLifeResearch/1.0"
MAX_BODY_BYTES = 32 * 1024 * 1024
MAX_JANUS_BYTES = 2 * 1024 * 1024


def _validate_target(raw):
    if not isinstance(raw, str) or len(raw) > 3000:
        raise ValueError("invalid_target")
    url = urlsplit(raw)
    host = (url.hostname or "").lower()
    if (url.scheme != "https" or host not in ALLOWED_HOSTS or url.port not in (None, 443)
            or url.username or url.password or url.fragment):
        raise ValueError("unapproved_target")
    if host == JANUS_HOST:
        if url.path != "/stock/api/getStockInfo.jsp":
            raise ValueError("unapproved_quote_path")
        q = parse_qs(url.query, keep_blank_values=True)
        if set(q) != {"ex_ch", "json", "delay"} or q["json"] != ["1"] or q["delay"] != ["0"]:
            raise ValueError("unapproved_quote_query")
        channels = q["ex_ch"][0].split("|") if len(q["ex_ch"]) == 1 else []
        if not 1 <= len(channels) <= 20 or any(not CHANNEL.fullmatch(ch) for ch in channels):
            raise ValueError("unapproved_quote_channels")
    # Resolve before access; only global addresses are eligible for outbound
    # calls. No redirect is ever followed. URL host is still TLS-verified.
    try:
        addresses = socket.getaddrinfo(host, 443, family=socket.AF_INET, type=socket.SOCK_STREAM)
        if not addresses or any(
            not ipaddress.ip_address(item[4][0]).is_global for item in addresses
        ):
            raise ValueError("nonpublic_destination")
    except (OSError, ValueError) as exc:
        raise ValueError("unresolvable_destination") from exc
    return host


@functions_framework.http
def proxy_request(req):
    # Cloud Run IAM must enforce the caller identity before the application.
    # Do not reinstate the previously embedded/public bearer token.
    if req.method != "POST" or not req.is_json:
        return jsonify({"error": "POST JSON required"}), 405
    data = req.get_json(silent=True)
    if not isinstance(data, dict) or set(data) - {"url", "method", "timeout", "headers"}:
        return jsonify({"error": "invalid_request"}), 400
    if str(data.get("method", "GET")).upper() != "GET":
        return jsonify({"error": "GET_only"}), 405
    try:
        host = _validate_target(data.get("url"))
    except (ValueError, TypeError):
        return jsonify({"error": "target_not_allowed"}), 400

    # Ignore caller-supplied headers, including Authorization, Host and Cookie.
    # Only fixed harmless request headers reach the public origin.
    headers = {"User-Agent": AGENT, "Accept": "application/json, */*"}
    if host == JANUS_HOST:
        headers["Referer"] = "https://mis.twse.com.tw/stock/index.jsp"
    try:
        timeout = max(1.0, min(20.0, float(data.get("timeout", 18.0 if host != JANUS_HOST else 8.0))))
    except (ValueError, TypeError):
        timeout = 8.0
    limit = MAX_JANUS_BYTES if host == JANUS_HOST else MAX_BODY_BYTES
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False, verify=True,
                          trust_env=False,
                          transport=httpx.HTTPTransport(verify=True, trust_env=False, local_address="0.0.0.0", retries=1)) as client:
            with client.stream("GET", data["url"], headers=headers) as upstream:
                if 300 <= upstream.status_code < 400:
                    return jsonify({"error": "upstream_redirect_rejected"}), 502
                if upstream.status_code != 200:
                    return jsonify({"error": "upstream_http_error",
                                    "status": upstream.status_code}), 502
                body = bytearray()
                for part in upstream.iter_bytes():
                    if len(body) + len(part) > limit:
                        return jsonify({"error": "upstream_response_too_large"}), 502
                    body.extend(part)
                mimetype = "application/json" if host == JANUS_HOST else (
                    upstream.headers.get("content-type", "application/octet-stream")
                    .split(";")[0])
                return Response(bytes(body), status=200, mimetype=mimetype,
                                headers={"Cache-Control": "no-store"})
    except (httpx.HTTPError, OSError, ValueError) as error:
        # Only a fixed exception class is returned; no upstream URL, body,
        # credentials or arbitrary exception messages are exposed.
        category = type(error).__name__
        if category not in {"ConnectError", "ConnectTimeout", "ReadTimeout", "WriteTimeout",
                            "ReadError", "RemoteProtocolError", "PoolTimeout", "OSError", "ValueError"}:
            category = "Unclassified"
        return jsonify({"error": "upstream_unavailable", "kind": category}), 502
