"""Local security contracts; never contact real external sites."""
from unittest.mock import patch

from flask import Flask, request
from services.tw_activity_proxy.main import _validate_target, proxy_request


def test_rejects_metadata_private_and_arbitrary_domains():
    app = Flask(__name__)
    urls = [
        "http://169.254.169.254/latest/meta-data/",
        "https://127.0.0.1/admin", "https://evil.example/anything",
        "https://mis.twse.com.tw/admin",
        "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_2382.tw&json=0&delay=0",
        "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_2382.tw%7Cevil.example&json=1&delay=0",
    ]
    for url in urls:
        with app.test_request_context("/", method="POST", json={"url": url}):
            assert proxy_request(request)[1] == 400


def test_rejects_private_dns_and_redirects():
    from services.tw_activity_proxy import main
    with patch.object(main.socket, "getaddrinfo",
                      return_value=[(2, 1, 6, "", ("10.0.0.5", 443))]):
        try:
            _validate_target("https://cloud.culture.tw/hello")
            assert False, "private DNS accepted"
        except ValueError:
            pass


def test_known_mis_channel_validates_and_does_not_forward_caller_auth():
    from services.tw_activity_proxy import main

    class Upstream:
        status_code = 200
        headers = {"content-type": "application/json"}
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def iter_bytes(self): yield b'{"rtcode":"0000","msgArray":[]}'

    class Client:
        def __init__(self, **kw):
            assert kw["verify"] is True
            assert kw["follow_redirects"] is False
            assert kw["trust_env"] is False
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def stream(self, method, url, headers):
            assert method == "GET"
            assert "Authorization" not in headers
            assert "Cookie" not in headers
            assert "mis.twse.com.tw" in url
            return Upstream()

    app = Flask(__name__)
    with patch.object(main.socket, "getaddrinfo",
                      return_value=[(2, 1, 6, "", ("8.8.8.8", 443))]), \
         patch.object(main.httpx, "Client", Client):
        with app.test_request_context("/", method="POST", json={
            "url": "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_2382.tw&json=1&delay=0",
            "headers": {"Authorization": "some-user-token", "Cookie": "private"},
        }):
            response = proxy_request(request)
            assert response.status_code == 200
            assert b'"rtcode":"0000"' in response.data


def test_ipv4_only_public_destination_and_safe_error_class():
    import socket
    import httpx
    from services.tw_activity_proxy import main
    app = Flask(__name__)
    target = "https://media.taiwan.net.tw/XMLReleaseAll_public/v2.0/Zh_tw/Event-json.zip"
    with patch.object(main.socket, "getaddrinfo",
                      return_value=[(socket.AF_INET, 1, 6, "", ("8.8.8.8", 443))]) as lookup, \\
         patch.object(main.httpx, "Client") as client:
        client.return_value.__enter__.return_value.stream.side_effect = httpx.ConnectTimeout("sensitive destination details")
        with app.test_request_context("/", method="POST", json={"url": target}):
            response, status = proxy_request(request)
            assert status == 502
            body = response.get_json()
            assert body == {"error": "upstream_unavailable", "kind": "ConnectTimeout"}
            assert "sensitive" not in str(body) and "media.taiwan" not in str(body)
        assert lookup.call_args.kwargs["family"] == socket.AF_INET
        assert client.call_args.kwargs["transport"] is not None
        assert client.call_args.kwargs["verify"] is True
        assert client.call_args.kwargs["trust_env"] is False
