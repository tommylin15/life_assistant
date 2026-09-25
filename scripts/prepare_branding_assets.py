#!/usr/bin/env python3
"""Generate Life Assistant branding assets from the high-resolution canonical icon."""
from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PARTS = tuple(
    ROOT / "branding" / f"life_assistant_icon_master.webp.b64.part{index:02d}"
    for index in range(1, 8)
)
EXPECTED_SOURCE_SHA256 = "3d5c034106daf674a62ec73bcb1b1ef6b124de6a2bdfc8ff3cba10fa7180db22"
EXPECTED_SOURCE_SIZE = (1024, 1024)
WARM_BG = (247, 243, 234, 255)


def _load_source() -> Image.Image:
    encoded = "".join(
        part.read_text(encoding="utf-8").strip() for part in SOURCE_PARTS
    )
    raw = base64.b64decode(encoded)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(f"Canonical icon SHA-256 mismatch: {actual}")
    image = Image.open(BytesIO(raw))
    if image.size != EXPECTED_SOURCE_SIZE:
        raise RuntimeError(f"Unexpected canonical icon size: {image.size}")
    return image.convert("RGBA")


def _save(image: Image.Image, path: Path, size: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.resize(size, Image.Resampling.LANCZOS).save(
        path,
        format="PNG",
        optimize=True,
    )


def _save_maskable(image: Image.Image, path: Path, size: int) -> None:
    canvas = Image.new("RGBA", (size, size), WARM_BG)
    inner = int(size * 0.80)
    icon = image.resize((inner, inner), Image.Resampling.LANCZOS)
    offset = (size - inner) // 2
    canvas.alpha_composite(icon, (offset, offset))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG", optimize=True)


def main() -> None:
    image = _load_source()
    web_icons = ROOT / "web" / "icons"

    # v8 is the current high-resolution branding set. Keep the older paths
    # regenerated from the same master so existing installs can refresh cleanly.
    for name in [
        "life-assistant-192-v8.png",
        "life-assistant-192-v7.png",
        "life-assistant-192-v6.png",
        "life-assistant-192-v5.png",
        "life-assistant-192-v2.png",
        "Icon-192.png",
    ]:
        _save(image, web_icons / name, (192, 192))

    for name in [
        "life-assistant-512-v8.png",
        "life-assistant-512-v7.png",
        "life-assistant-512-v6.png",
        "life-assistant-512-v5.png",
        "life-assistant-512-v2.png",
        "Icon-512.png",
    ]:
        _save(image, web_icons / name, (512, 512))

    for name in [
        "life-assistant-maskable-192-v8.png",
        "life-assistant-maskable-192-v7.png",
        "life-assistant-maskable-192-v6.png",
        "Icon-maskable-192.png",
    ]:
        _save_maskable(image, web_icons / name, 192)

    for name in [
        "life-assistant-maskable-512-v8.png",
        "life-assistant-maskable-512-v7.png",
        "life-assistant-maskable-512-v6.png",
        "Icon-maskable-512.png",
    ]:
        _save_maskable(image, web_icons / name, 512)

    _save(image, ROOT / "web" / "favicon.png", (192, 192))
    _save(image, ROOT / "web" / "branding" / "life-assistant-hero-v8.png", (1024, 1024))
    _save(image, ROOT / "web" / "branding" / "life-assistant-hero-v7.png", (1024, 1024))
    _save(image, ROOT / "web" / "branding" / "life-assistant-hero-v6.png", (1024, 1024))

    _save(
        image,
        ROOT / "android" / "app" / "src" / "main" / "res" / "drawable" / "life_assistant_icon.png",
        (1024, 1024),
    )
    for density, size in {
        "mdpi": 48,
        "hdpi": 72,
        "xhdpi": 96,
        "xxhdpi": 144,
        "xxxhdpi": 192,
    }.items():
        _save(
            image,
            ROOT / "android" / "app" / "src" / "main" / "res" / f"mipmap-{density}" / "ic_launcher.png",
            (size, size),
        )

    print(
        "Prepared Life Assistant branding assets from verified "
        f"{EXPECTED_SOURCE_SIZE[0]}px twin-beast master icon."
    )


if __name__ == "__main__":
    main()
