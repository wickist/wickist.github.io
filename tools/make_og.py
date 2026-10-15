#!/usr/bin/env python3
"""1200x630 X/OpenGraph kapakları üretir (PIL).

Kullanım:
  python3 tools/make_og.py                 # tüm raporlar + site fallback
  python3 tools/make_og.py --only T:P      # yalnız seçili rapor(lar) + site fallback

Tasarım (15.10.2026, kullanıcı onayı): raporun kendi paleti ve fontları —
kâğıt zemin #F0EEE6, çini #B0472A, amber/turuncu vurgu, Fraunces başlık +
Inter gövde. Yaprak logosu sol üstte ÇERÇEVESİZ ve yumuşak kenarlı, zemine
eriyerek oturur; kapağın doğal parçasıdır.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 630
PAPER = (234, 230, 217)    # #EAE6D9 — kirli beyaz (saf beyaz değil)
INK = (31, 30, 29)         # #1F1E1D
SOFT = (60, 58, 53)        # #3C3A35
MUTED = (107, 103, 94)     # #6B675E
CLAY = (176, 71, 42)       # #B0472A — rapor aksanı
AMBER = (228, 185, 106)    # #E4B96A — rapor amber vurgusu
RULE = (216, 210, 192)     # hairline
BAND = (228, 185, 106)     # #E4B96A — alt bant: dönem rozetiyle aynı amber
FDIR = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "images" / "logo.png"   # CYCLE yaprak logosu — her kapakta zorunlu
SEAL = ROOT / "assets" / "images" / "seal.png"   # monokrom CYCLE mührü — telif yanında
EYEBROW = "BIST · KAP KAYNAKLI · BAĞIMSIZ ANALİZ"
COPYRIGHT = "© 2026 Enis Halıcı · Tüm hakları saklıdır."


def frac(size: int, wght: int = 700, opsz: int = 144) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FDIR / "Fraunces-VF.ttf"), size)
    f.set_variation_by_axes([opsz, wght, 50, 0])   # OpticalSize, Weight, Softness, Wonky
    return f


def inter(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FDIR / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf")), size)


def spaced(d: ImageDraw.ImageDraw, xy, text: str, f, fill, track: int) -> float:
    """Harf aralıklı (letter-spacing) metin basar; sağ kenar x döner."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + track
    return x - track


def paste_logo_soft(img: Image.Image, x: int = 40, y: int = 24, h: int = 300) -> None:
    """Logoyu sol üste çerçevesiz basar; kenarları gauss ile eritip kâğıt zeminde kaybeder."""
    if not LOGO.exists():
        return
    iw, ih = Image.open(LOGO).size
    w = int(round(h * iw / ih))
    logo = Image.open(LOGO).convert("RGBA").resize((w, h), Image.LANCZOS)
    pad = int(h * 0.12)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((pad, pad, w - pad, h - pad), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(int(h * 0.15)))
    img.paste(logo, (x, y), mask)


def paste_seal(img: Image.Image, x: int, y: int, h: int = 62) -> None:
    """Mührü alt bandın üstüne eriterek basar: kâğıt tonu kanala göre beyaza
    normalize edilir (kare kenar/çerçeve izi kaybolur, bantla birebir kaynaşır),
    mürekkep çizgileri multiply ile kalır; kenarlara yumuşak maske verilir."""
    if not SEAL.exists():
        return
    iw, ih = Image.open(SEAL).size
    w = int(round(h * iw / ih))
    seal = Image.open(SEAL).convert("RGB").resize((w, h), Image.LANCZOS)
    # kenar şeridinin medyanı = kâğıt tonu; kanal bazında 255'e ölçekle
    strip = list(seal.crop((0, 0, w, max(2, h // 25))).getdata()) + \
        list(seal.crop((0, h - max(2, h // 25), w, h)).getdata())
    p = [sorted(px[c] for px in strip)[len(strip) // 2] for c in range(3)]
    norm = Image.merge("RGB", [ch.point(lambda v, pc=pc: min(255, v * 255 // pc))
                               for ch, pc in zip(seal.split(), p)])
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((w // 20, h // 20, w - w // 20, h - h // 20), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(h // 10))
    patch = img.crop((x, y, x + w, y + h))
    img.paste(ImageChops.multiply(patch, norm), (x, y), mask)


def draw_cover(path: Path, ticker: str, period_label: str, subtitle: str,
               sections: str, company: str) -> None:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 80, W, H), fill=BAND)   # silik yaprak bandı — şirket/URL kısmı
    paste_logo_soft(img)
    x0 = 400
    # künye: amber kare + aralıklı küçük harf
    d.rectangle((x0, 104, x0 + 11, 115), fill=AMBER)
    spaced(d, (x0 + 26, 99), EYEBROW, inter(20, True), MUTED, 2)
    # ticker — Fraunces
    d.text((x0 - 4, 132), ticker, font=frac(100, 700), fill=INK)
    # dönem rozeti — amber zemin, çini yazı
    label = period_label.strip()
    f_per = inter(34, True)
    tw = d.textlength(label, font=f_per)
    y = 268
    d.rounded_rectangle((x0, y, x0 + tw + 44, y + 58), radius=12, fill=AMBER)
    d.text((x0 + 22, y + 10), label, font=f_per, fill=CLAY)
    # hairline
    d.line((48, 368, W - 48, 368), fill=RULE, width=2)
    # başlık + satır
    d.text((48, 396), subtitle, font=frac(52, 600, 96), fill=INK)
    d.text((48, 486), sections, font=inter(29), fill=MUTED)
    # üst bant çizgisi üstü: site URL'i sağa yaslı
    url = "wickist.github.io"
    d.text((W - 48 - d.textlength(url, font=inter(21, True)), H - 112),
           url, font=inter(21, True), fill=CLAY)
    # alt bant: solda şirket, sağda telif + mühür (mühür bandın amberine multiply ile biner)
    d.text((48, H - 54), company, font=inter(23), fill=SOFT)
    f_cr = inter(21)
    sx = W - 48 - 62
    d.text((sx - 18 - d.textlength(COPYRIGHT, font=f_cr), H - 52), COPYRIGHT,
           font=f_cr, fill=SOFT)
    paste_seal(img, sx, H - 71)
    img.save(path, "PNG", optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="OG kapakları; --only TICKER:PERIOD ile yalnız seçili raporlar")
    ap.add_argument("--only", action="append", metavar="TICKER:PERIOD")
    a = ap.parse_args()
    only = set(a.only or [])
    reg = json.loads((ROOT / "data" / "reports.json").read_text(encoding="utf-8"))
    made = 0
    for r in reg["reports"]:
        if only and f"{r['ticker']}:{r['period']}" not in only:
            continue
        out = ROOT / r["ogImage"].lstrip("/")
        out.parent.mkdir(parents=True, exist_ok=True)
        draw_cover(
            out,
            ticker=r["ticker"],
            period_label=r["periodLabel"],
            subtitle=r.get("coverSubtitle", "Finansal Analiz Raporu"),
            sections=r.get("coverSections", "Bilanço • Gelir Tablosu • Nakit Akışı • Oran Analizi"),
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
