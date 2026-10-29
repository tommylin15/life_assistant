"""Life Omni LINE eight-grid art generator (Pillow, Noto Sans CJK).

Usage:
  python -m pip install Pillow
  python scripts/build_line_rich_menu_v2.py --out /tmp/line-v2.jpg --mascot /path/to/owner-twin-beasts.png

Owner's supplied golden/blue twin-beast graphic is an optional source asset.
It is not fetched from an unauthenticated third-party URL. No LINE API calls.
"""
import argparse
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from line_rich_menu_v2 import LABELS, menu, verify_image

FONT_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
SIZE = (2500, 1686)
GREEN = (25, 88, 68)
SUBS = ("隨手寫下・即時保存", "今日待辦・行程摘要", "搜尋生活留存資料", "查看清單・快速完成",
        "採買項目・即時勾選", "查看近期行程", "最新活動・分類收藏", "進入完整生活管理")
PALETTE = ((31,112,84),(236,249,241),(248,254,250),(246,252,249),
           (247,251,250),(243,250,244),(239,250,246),(247,253,250))


def _font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_B if bold else FONT_R, size)
    except OSError:
        return ImageFont.truetype("DejaVuSans.ttf", size)


def _icon(d, label, cx, cy, color):
    lw = 17
    if label == "快速記錄":
        d.rounded_rectangle((cx-90,cy-110,cx+72,cy+99),radius=18,outline=color,width=lw)
        for k in (-45,-1,43): d.line((cx-52,cy+k,cx+28,cy+k),fill=color,width=11)
        d.polygon(((cx+35,cy+87),(cx+103,cy+23),(cx+119,cy+42),(cx+54,cy+110)),fill=(236,189,111))
    elif label in ("今日總覽","日曆"):
        d.rounded_rectangle((cx-98,cy-95,cx+98,cy+94),radius=19,outline=color,width=lw)
        d.rectangle((cx-92,cy-54,cx+92,cy-27),fill=color)
        for k in (-50,50): d.line((cx+k,cy-128,cx+k,cy-70),fill=color,width=lw)
        if label=="今日總覽":
            d.ellipse((cx-61,cy+2,cx-11,cy+52),fill=(110,185,144))
            d.line((cx-50,cy+22,cx-35,cy+39,cx-12,cy+7),fill=(255,255,255),width=9)
        else:
            d.arc((cx-37,cy-10,cx+69,cy+90),185,350,fill=color,width=11)
            d.line((cx+18,cy+44,cx+18,cy+6),fill=color,width=9)
            d.line((cx+18,cy+44,cx+48,cy+66),fill=color,width=9)
    elif label == "查我的資料":
        d.ellipse((cx-86,cy-88,cx+38,cy+36),outline=color,width=lw)
        d.line((cx+32,cy+29,cx+106,cy+105),fill=color,width=lw)
    elif label == "待辦":
        for yy in (-72,0,72):
            d.rounded_rectangle((cx-95,cy+yy-17,cx-60,cy+yy+17),radius=5,outline=color,width=9)
            d.line((cx-87,cy+yy,cx-72,cy+yy+12,cx-48,cy+yy-12),fill=(42,159,112),width=10)
            d.line((cx-28,cy+yy,cx+107,cy+yy),fill=color,width=12)
    elif label == "購物":
        d.arc((cx-64,cy-130,cx+64,cy-17),180,360,fill=color,width=16)
        d.rounded_rectangle((cx-99,cy-55,cx+99,cy+101),radius=16,outline=color,width=lw)
        d.line((cx-55,cy-10,cx+55,cy-10),fill=color,width=11)
    elif label == "活動":
        d.rounded_rectangle((cx-95,cy-84,cx+99,cy+78),radius=21,outline=color,width=lw)
        d.polygon([(cx,cy-55),(cx+24,cy-11),(cx+70,cy+1),(cx+35,cy+35),
                   (cx+42,cy+80),(cx,cy+52),(cx-41,cy+78),(cx-34,cy+35),
                   (cx-71,cy+2),(cx-26,cy-12)],fill=(236,196,100))
    else:
        for sign,fill in ((-1,(241,193,110)),(1,(35,82,107))):
            px=cx+sign*67
            d.ellipse((px-94,cy-73,px+94,cy+95),fill=fill)
            d.polygon((px-75,cy-40,px-121,cy-127,px-14,cy-83),fill=fill)
            d.polygon((px+20,cy-73,px+100,cy-135,px+82,cy-23),fill=fill)
            for delta in (-29,29):
                d.ellipse((px+delta-10,cy-5,px+delta+12,cy+19),fill=(255,252,235))


def _paste_mascot(image, draw, source, cx, cy):
    if not source:
        _icon(draw, "Life Omni", cx, cy, GREEN)
        return
    beast = Image.open(source).convert("RGB")
    w,h = beast.size
    if .8 < w/h < 1.3:
        beast=beast.crop((int(w*.12),int(h*.34),int(w*.9),int(h*.88)))
    edge=min(beast.size); xx=(beast.width-edge)//2; yy=(beast.height-edge)//2
    beast=beast.crop((xx,yy,xx+edge,yy+edge)).resize((286,286),Image.Resampling.LANCZOS)
    mask=Image.new("L",(286,286),0)
    ImageDraw.Draw(mask).ellipse((0,0,285,285),fill=255)
    image.paste(beast,(cx-143,cy-143),mask)
    draw.ellipse((cx-144,cy-144,cx+144,cy+144),outline=(255,255,255),width=9)


def render(mascot: Path | None = None, *, positions: bool = False) -> Image.Image:
    image=Image.new("RGB", SIZE, (232,247,237))
    d=ImageDraw.Draw(image)
    for box in ((-750,-580,1080,730),(1700,-530,3250,590),
                (-900,1140,1000,2400),(1650,1060,3450,2300)):
        d.ellipse(box,fill=(217,240,221))
    specs=menu("https://gen-lang-client-0593591102.web.app/today")["areas"]
    for i, (name, area) in enumerate(zip(LABELS,specs)):
        b=area["bounds"]; x,y=b["x"],b["y"]; cx=x+312; cy=y+280
        rect=(x+20,y+24,x+605,y+819)
        d.rounded_rectangle((x+28,y+34,x+613,y+831),radius=64,fill=(207,228,213))
        d.rounded_rectangle(rect,radius=64,fill=PALETTE[i],outline=(255,255,255),width=8)
        d.ellipse((cx-152,cy-152,cx+152,cy+152),fill=(44,138,104) if i==0 else (209,238,221))
        if i==7: _paste_mascot(image,d,mascot,cx,cy)
        else: _icon(d,name,cx,cy,(255,255,255) if i==0 else GREEN)
        label_font=_font(62 if name=="查我的資料" else 69 if i!=7 else 66,True)
        left,top,right,bottom=d.textbbox((0,0),name,font=label_font)
        d.text((cx-(right-left)/2,y+532),name,font=label_font,
               fill=(255,255,255) if i==0 else GREEN)
        sub_font=_font(30); left,top,right,bottom=d.textbbox((0,0),SUBS[i],font=sub_font)
        d.text((cx-(right-left)/2,y+665),SUBS[i],font=sub_font,
               fill=(220,249,228) if i==0 else (80,124,108))
        d.ellipse((x+45,y+50,x+107,y+112),fill=(237,255,244))
        d.text((x+72,y+49),str(i+1),font=_font(32,True),fill=GREEN)
        if positions:
            d.rectangle((x+3,y+3,x+622,y+840),outline=(236,62,42),width=9)
            d.text((x+30,y+131),f'{x},{y},625,843',font=_font(29,True),fill=(158,28,19))
    return image


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mascot",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--positions",action="store_true",help="Guide ONLY; never upload to LINE")
    options=parser.parse_args()
    image=render(options.mascot,positions=options.positions)
    options.out.parent.mkdir(parents=True,exist_ok=True)
    for quality in (88,82,75,68,60,54,47):
        image.save(options.out,format="JPEG",quality=quality,optimize=True,subsampling=2)
        if options.out.stat().st_size<=1_000_000:break
    verify_image(options.out)
    print(f'LINE_IMAGE=PASS {options.out.stat().st_size} bytes {options.out}')


if __name__=="__main__":
    main()
