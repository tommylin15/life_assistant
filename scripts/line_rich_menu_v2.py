"""Life Omni LINE v2 eight-grid Rich Menu: JSON contract and explicit API apply.

Keeps the existing six-grid script untouched. Never applies without --apply.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

WIDTH, HEIGHT = 2500, 1686
LABELS = ("快速記錄", "今日總覽", "查我的資料", "待辦", "購物", "日曆", "活動", "Life Omni")
COMMANDS = ("capture.start", "today.view", "search.start", "tasks.list",
            "shopping.list", "calendar.today", "events.latest", None)
HOSTS = frozenset(("gen-lang-client-0593591102.web.app",
                   "life-assistant-v3-stage-tl15.web.app"))


def life_url(url: str) -> str:
    u = urlsplit(url)
    if (u.scheme != "https" or u.hostname not in HOSTS
            or u.port not in (None, 443) or u.username or u.password
            or u.query or u.fragment or u.path not in ("", "/", "/today")):
        raise ValueError("Only approved Life Hosting HTTPS /today URL is allowed")
    return f"https://{u.hostname}/today"


def menu(app_url: str) -> dict:
    destination = life_url(app_url)
    areas = []
    for i, (label, command) in enumerate(zip(LABELS, COMMANDS)):
        bounds = {"x": (i % 4) * 625, "y": (i // 4) * 843,
                  "width": 625, "height": 843}
        action = ({"type": "postback", "label": label, "data": "v=2&cmd=" + command}
                  if command else {"type": "uri", "label": label, "uri": destination})
        areas.append({"bounds": bounds, "action": action})
    return {"size": {"width": WIDTH, "height": HEIGHT}, "selected": True,
            "name": "Life Omni v2 - Eight Grid",
            "chatBarText": "Life Omni 生活助手", "areas": areas}


def verify_image(path: Path) -> str:
    from PIL import Image
    if path.stat().st_size > 1_000_000:
        raise ValueError("Rich Menu image exceeds 1 MB")
    with Image.open(path) as picture:
        if picture.size != (WIDTH, HEIGHT) or picture.format not in ("JPEG", "PNG"):
            raise ValueError("Image must be JPEG/PNG 2500x1686")
        return "image/jpeg" if picture.format == "JPEG" else "image/png"


def apply(body: dict, image: Path, token: str) -> str:
    if not token or len(token) < 32:
        raise ValueError("Missing LINE Messaging API Channel Access Token")
    mime = verify_image(image)
    def request(url, data=None, content_type=None):
        headers = {"Authorization": "Bearer " + token}
        if content_type:
            headers["Content-Type"] = content_type
        r = Request(url, data=data, headers=headers,
                    method="POST" if data is not None else "GET")
        try:
            with urlopen(r, timeout=30) as response:
                text = response.read()
                return json.loads(text) if text else {}
        except HTTPError as error:
            raise RuntimeError(f"LINE API HTTP {error.code}") from None
    new_id = request("https://api.line.me/v2/bot/richmenu",
                     json.dumps(body, ensure_ascii=False).encode(), "application/json")["richMenuId"]
    request(f"https://api-data.line.me/v2/bot/richmenu/{new_id}/content",
            image.read_bytes(), mime)
    request(f"https://api.line.me/v2/bot/user/all/richmenu/{new_id}", b"", "application/json")
    actual = request("https://api.line.me/v2/bot/user/all/richmenu").get("richMenuId")
    if actual != new_id:
        raise RuntimeError("LINE default Rich Menu readback mismatch")
    return new_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--life-url", required=True)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    body = menu(args.life_url)
    print(json.dumps(body, ensure_ascii=False, indent=2))
    if args.image:
        print("image_mime=" + verify_image(args.image))
    if args.apply:
        if not args.image:
            parser.error("--image required for --apply")
        token = os.environ.get("LIFE_LINE_ACCESS_TOKEN", "")
        try:
            print("LINE_V2_DEFAULT_MENU_API=PASS richMenuId=" + apply(body, args.image, token))
        except (ValueError, RuntimeError) as error:
            parser.error(str(error))


if __name__ == "__main__":
    main()
