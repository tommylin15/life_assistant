#!/usr/bin/env python3
"""Render the six-cell Life LINE rich menu; never calls the LINE API.

Usage: python scripts/build_line_rich_menu.py --out /tmp/life-line-rich-menu.png
Requires optional design-only dependency: python -m pip install cairosvg==2.8.2
"""
import argparse
from html import escape
from pathlib import Path
import struct
from importlib.util import module_from_spec, spec_from_file_location

# The order and clickable grid are owned by scripts/line_rich_menu.py.
_menu_spec = spec_from_file_location("_life_line_rich_menu", Path(__file__).with_name("line_rich_menu.py"))
_menu_module = module_from_spec(_menu_spec)
_menu_spec.loader.exec_module(_menu_module)
menu = _menu_module.menu

SUBTITLES = (
    "隨手記下靈感", "掌握今天安排", "搜尋個人紀錄",
    "清單一次管理", "查看行程與探索", "回到生活中心",
)
ICONS = (
    "M4 20l4-1 11-11-3-3L5 16l-1 4z M14 7l3 3",
    "M4 5h16v16H4z M8 2v6 M16 2v6 M4 11h16 M8 15h3 M14 15h3 M8 18h3",
    "M11 18a7 7 0 1 0 0-14 7 7 0 1 0 0 14z M16.5 16.5L21 21",
    "M3 7l2 2 4-4 M12 7h9 M3 17l2 2 4-4 M12 17h9",
    "M4 5h16v16H4z M8 2v6 M16 2v6 M4 11h16 M9 16l2 2 4-4",
    "M12 13a5 5 0 1 0 0-10 5 5 0 1 0 0 10z M3 21c0-7 18-7 18 0",
)


def svg_markup() -> str:
    grid = menu("123-preview")
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="2500" height="1686" viewBox="0 0 2500 1686">',
        '<rect width="2500" height="1686" fill="#E1EBE6"/>',
    ]
    for index, area in enumerate(grid["areas"]):
        b = area["bounds"]
        x, y, w, h = (b[k] for k in ("x", "y", "width", "height"))
        cx = x + w / 2
        dark = index == 0
        fill = "#175A48" if dark else ("#F7FAF8" if index % 2 == 0 else "#EAF2ED")
        fg = "#FFFFFF" if dark else "#163D36"
        muted = "#D7EBDF" if dark else "#537168"
        circle = "#2A735C" if dark else "#D8E9DD"
        glyph = "#FFFFFF" if dark else "#236B55"
        parts.extend([
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>',
            f'<path d="M{x+38} {y+40}h120" stroke="{muted}" stroke-width="8" stroke-linecap="round" opacity="0.55"/>',
            f'<circle cx="{cx:g}" cy="{y+272}" r="122" fill="{circle}"/>',
            f'<g transform="translate({cx-76:g} {y+196}) scale(6.333333)" fill="none" stroke="{glyph}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="{ICONS[index]}"/></g>',
            f'<text x="{cx:g}" y="{y+543}" text-anchor="middle" font-family="Noto Sans CJK TC,Noto Sans TC,sans-serif" font-size="100" font-weight="800" fill="{fg}">{escape(area["action"]["label"])}</text>',
            f'<text x="{cx:g}" y="{y+645}" text-anchor="middle" font-family="Noto Sans CJK TC,Noto Sans TC,sans-serif" font-size="56" font-weight="400" fill="{muted}">{SUBTITLES[index]}</text>',
            f'<text x="{cx:g}" y="{y+762}" text-anchor="middle" font-family="sans-serif" font-size="29" letter-spacing="7" font-weight="700" fill="{muted}" opacity="0.75">LIFE  /  {index+1:02d}</text>',
        ])
    # Dividers match the six exact tappable bounds: x=0/833/1666/2500, y=0/843/1686.
    parts.extend([
        '<path d="M833 0V1686 M1666 0V1686 M0 843H2500" fill="none" stroke="#C9DAD0" stroke-width="4"/>',
        '</svg>',
    ])
    return '\n'.join(parts)


def verify_png(path: Path) -> int:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24:
        raise ValueError("Image is not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (2500, 1686):
        raise ValueError(f"Unexpected PNG size: {width}x{height}")
    if len(data) > 1_000_000:
        raise ValueError(f"LINE image exceeds 1 MB: {len(data)} bytes")
    return len(data)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True, help="Output PNG; will not upload to LINE")
    p.add_argument("--svg-out", type=Path, help="Optional editable SVG preview")
    args = p.parse_args()
    svg = svg_markup().encode("utf-8")
    if args.svg_out:
        args.svg_out.parent.mkdir(parents=True, exist_ok=True)
        args.svg_out.write_bytes(svg)
    try:
        import cairosvg
    except ImportError as exc:
        p.error("Install design-only dependency: python -m pip install cairosvg==2.8.2")
        raise AssertionError from exc
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svg, write_to=str(args.out))
    print(f"rich_menu_image=PASS dimensions=2500x1686 bytes={verify_png(args.out)} path={args.out}")


if __name__ == "__main__":
    main()
