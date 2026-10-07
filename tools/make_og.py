#!/usr/bin/env python3
"""1200x630 X/OpenGraph kapakları üretir (PIL, DejaVu).

Kullanım:
  python3 tools/make_og.py            # reports.json içindeki tüm raporlar + site fallback
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 630
BG = (31, 30, 29)          # #1F1E1D — rapor paleti
PANEL = (46, 44, 42)
GOLD = (201, 162, 39)      # #C9A227
FG = (237, 234, 228)
MUTED = (167, 162, 155)
LINE = (90, 86, 80)
F = "/usr/share/fonts/truetype/dejavu/"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(F + name, size)


def draw_cover(path: Path, ticker: str, period_label: str, subtitle: str,
               sections: str, company: str) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # ince üst şerit + panel çizgileri
    d.rectangle((0, 0, W, 10), fill=GOLD)
    d.line((0, H - 74, W, H - 74), fill=LINE, width=2)
    # ticker
    d.text((70, 84), ticker, font=font("DejaVuSans-Bold.ttf", 96), fill=GOLD)
    # dönem rozeti
    label = f"  {period_label}  "
    f_per = font("DejaVuSans-Bold.ttf", 44)
    tw = d.textlength(label, font=f_per)
    y = 232
    d.rounded_rectangle((70, y, 70 + tw + 24, y + 66), radius=12, fill=PANEL, outline=GOLD, width=2)
    d.text((82, y + 8), label, font=f_per, fill=FG)
    # başlık
    d.text((70, 348), subtitle, font=font("DejaVuSans-Bold.ttf", 52), fill=FG)
    d.text((70, 424), sections, font=font("DejaVuSans.ttf", 34), fill=MUTED)
    # alt bant
    d.text((70, H - 58), company, font=font("DejaVuSans.ttf", 26), fill=MUTED)
    d.text((W - 70 - d.textlength("wickist.github.io", font=font("DejaVuSans.ttf", 26)),
            H - 58), "wickist.github.io", font=font("DejaVuSans.ttf", 26), fill=GOLD)
    img.save(path, "PNG", optimize=True)


def main() -> None:
    reg = json.loads((ROOT / "data" / "reports.json").read_text(encoding="utf-8"))
    made = 0
    for r in reg["reports"]:
        out = ROOT / r["ogImage"].lstrip("/")
        out.parent.mkdir(parents=True, exist_ok=True)
        draw_cover(
            out,
            ticker=r["ticker"],
            period_label=r["periodLabel"],
            subtitle="Finansal Analiz Raporu",
            sections="Bilanço • Gelir Tablosu • Nakit Akışı • Oran Analizi",
            company=r["company"],
        )
        made += 1
    fallback = ROOT / "assets" / "images" / "site-og.png"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    draw_cover(
        fallback,
        ticker="BIST",
        period_label="Portal",
        subtitle="Finansal Analiz Raporları",
        sections="Bilanço • Nakit Akışı • Özkaynak • Oran Analizi",
        company="KAP kaynaklı şirket analiz arşivi",
    )
    print(f"OK: {made} rapor kapağı + site fallback üretildi")


if __name__ == "__main__":
    main()
