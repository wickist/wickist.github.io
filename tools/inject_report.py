#!/usr/bin/env python3
"""Rapor HTML'ini site yapısına yerleştirir: head metadata + breadcrumb + disclaimer.

Kullanım:
  python3 tools/inject_report.py --source <rapor.html> --ticker EREGL \
      --period 2026-Q2 --period-label "2026 H1" --company "..." \
      --title "..." --description "..." [--published YYYY-MM-DD] [--updated YYYY-MM-DD] \
      [--tags a,b,c]

Rapor içeriğine (tablo/grafik/dipnot/hesap) DOKUNMAZ; yalnız üç ekleme yapar:
head'e sosyal/SEO metadata bloğu, body başına breadcrumb, body sonuna uyarı satırı.
reports.json kaydı ekler/günceller (ticker+period tekil anahtar).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://wickist.github.io"
MARKER_HEAD = "<!-- site-publish:meta -->"
MARKER_FOOT = "<!-- site-publish:footer -->"
SITE_NAME = "Finansal Analiz Raporları"
FOOTER_HTML = """{marker}
<footer style="max-width:1080px;margin:26px auto 0;padding:14px 20px 22px;border-top:1px solid
 #E3DED2;font-size:12px;color:#5D594D">
Bu içerik yatırım tavsiyesi değildir. Veriler KAP kamuyu aydınlatma platformu
kaynaklıdır; analiz yorum içerir. ·
<a href="/" style="color:#B0472A">Ana Sayfa</a> ·
<a href="/reports/{ticker}/" style="color:#B0472A">Tüm {ticker} Raporları</a>
</footer>
"""

NAV_HTML = """{marker}
<nav style="max-width:1080px;margin:0 auto;padding:10px 20px;font-size:13px;
 color:#5D594D;border-bottom:1px solid #E3DED2">
<a href="/" style="color:#5D594D;text-decoration:none">Ana Sayfa</a> /
<a href="/reports/{ticker}/" style="color:#5D594D;text-decoration:none">{ticker}</a> /
<span style="color:#B0472A;font-weight:600">{period_label}</span>
</nav>
"""


def head_block(args: argparse.Namespace) -> str:
    url = f"{BASE}{args.path}"
    img = f"{BASE}{args.path}og-cover.png"
    desc = args.description
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": args.title,
        "description": desc,
        "inLanguage": "tr",
        "datePublished": args.published,
        "dateModified": args.updated,
        "url": url,
        "image": img,
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "about": {"@type": "Organization", "name": args.company, "tickerSymbol": args.ticker},
    }
    return f"""{MARKER_HEAD}
<title>{escape(args.title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{escape(args.title)}">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{escape(args.title)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(args.title)}">
<meta name="twitter:description" content="{escape(desc)}">
<meta name="twitter:image" content="{img}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
"""


def patch_html(source: Path, args: argparse.Namespace) -> str:
    html = source.read_text(encoding="utf-8")
    if MARKER_HEAD in html:
        raise SystemExit("kaynak zaten yayınlanmış görünüyor (marker var) — orijinal dosyayı verin")
    m = re.search(r"[ \t]*<title>.*?</title>\n?", html, flags=re.S)
    if not m:
        raise SystemExit("<title> bulunamadı — head yapısı beklenmedik")
    html = html[: m.start()] + head_block(args) + html[m.end():]
    m = re.search(r"<body[^>]*>\n?", html)
    if not m:
        raise SystemExit("<body> bulunamadı")
    nav = NAV_HTML.format(marker=MARKER_HEAD, ticker=args.ticker,
                          period_label=args.period_label)
    html = html[: m.end()] + nav + html[m.end():]
    idx = html.rfind("</body>")
    if idx < 0:
        raise SystemExit("</body> bulunamadı")
    html = html[:idx] + FOOTER_HTML.format(marker=MARKER_FOOT, ticker=args.ticker) + html[idx:]
    return html


def update_registry(args: argparse.Namespace) -> None:
    reg_path = ROOT / "data" / "reports.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    entry = {
        "ticker": args.ticker,
        "company": args.company,
        "period": args.period,
        "periodLabel": args.period_label,
        "year": int(args.period.split("-")[0]),
        "quarter": int(args.period.split("Q")[1]),
        "title": args.title,
        "description": args.description,
        "publishedAt": args.published,
        "updatedAt": args.updated,
        "path": args.path,
        "ogImage": args.path + "og-cover.png",
        "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
    }
    reports = [r for r in reg["reports"]
               if not (r["ticker"] == args.ticker and r["period"] == args.period)]
    reports.append(entry)
    reg["reports"] = reports
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--ticker", required=True)
    p.add_argument("--period", required=True, help="YYYY-QN")
    p.add_argument("--period-label", required=True, help="ör. 2026 H1")
    p.add_argument("--company", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--published", required=True)
    p.add_argument("--updated", required=True)
    p.add_argument("--tags", default="bilanço,finansal analiz")
    args = p.parse_args()
    if not re.fullmatch(r"\d{4}-Q[1-4]", args.period):
        sys.exit("period YYYY-Q1..Q4 olmalı")
    args.path = f"/reports/{args.ticker}/{args.period}/"
    out = ROOT / "reports" / args.ticker / args.period
    out.mkdir(parents=True, exist_ok=True)
    patched = patch_html(Path(args.source), args)
    (out / "index.html").write_text(patched, encoding="utf-8")
    update_registry(args)
    print(f"OK: {args.ticker} {args.period} -> {out}/index.html + reports.json")


if __name__ == "__main__":
    main()
