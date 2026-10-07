#!/usr/bin/env python3
"""Portal üretici: data/reports.json -> index.html, şirket indeksleri, sitemap.xml.

Kullanım: python3 tools/build_site.py
Yeni rapor eklendiğinde (reports.json güncellendikten sonra) çalıştırılır;
statik, crawlable HTML üretir. JS yalnız arama/filtre iyileştirmesidir.
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_NAME = "Finansal Analiz Raporları"
BASE = "https://wickist.github.io"


def load() -> dict:
    return json.loads((ROOT / "data" / "reports.json").read_text(encoding="utf-8"))


def sort_reports(reports: list[dict]) -> list[dict]:
    return sorted(
        reports,
        key=lambda r: (r["year"], r["quarter"], r["updatedAt"], r["ticker"]),
        reverse=True,
    )


def head(title: str, description: str, path: str, og_image: str | None = None) -> str:
    canonical = f"{BASE}{path}"
    og = f'{og_image or BASE + "/assets/images/site-og.png"}'
    og_abs = og if og.startswith("http") else BASE + og
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{escape(og_abs)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(title)}">
<meta name="twitter:description" content="{escape(description)}">
<meta name="twitter:image" content="{escape(og_abs)}">
<link rel="stylesheet" href="/assets/css/site.css">
</head>
"""


def header_block() -> str:
    return f"""<header class="site"><div class="wrap">
<h1><a href="/" style="color:inherit">{SITE_NAME}</a></h1>
<span class="sub">BIST şirketleri · bilanço ve finansal tablo analizleri · KAP kaynaklı</span>
</div></header>
"""


def footer() -> str:
    return """<footer class="site"><div class="wrap">
Bu içerik yatırım tavsiyesi değildir. Tüm veriler KAP kamuyu aydınlatma
platformu kaynaklıdır; analiz yorum içerir.
</div></footer>
"""


def card(r: dict, show_ticker: bool = True) -> str:
    search = f"{r['ticker']} {r['company']} {r['period']} {r['periodLabel']} {r['year']} {r['title']}"
    ticker_line = f"{r['ticker']} · {r['periodLabel']}" if show_ticker else r["periodLabel"]
    return f"""<div class="card" data-card data-search="{escape(search)}" data-year="{r['year']}" data-quarter="{r['quarter']}">
<span class="period">{escape(ticker_line)}</span>
<span class="title">{escape(r['title'])}</span>
<span class="desc">{escape(r['description'])}</span>
<span class="meta">Güncelleme: {escape(r['updatedAt'])}</span>
<a class="open" href="{escape(r['path'])}">Raporu Aç</a>
</div>"""


def build_index(data: dict) -> None:
    reports = sort_reports(data["reports"])
    tickers = {}
    for r in reports:
        tickers.setdefault(r["ticker"], []).append(r)
    years = sorted({r["year"] for r in reports}, reverse=True)
    quarters = sorted({r["quarter"] for r in reports})

    filters = ['<button data-filter="all">Tümü</button>']
    filters += [f'<button data-filter="year:{y}">{y}</button>' for y in years]
    filters += [f'<button data-filter="quarter:{q}">Q{q}</button>' for q in quarters]

    blocks = []
    for ticker in sorted(tickers):
        rs = tickers[ticker]
        cards = "\n".join(card(r, show_ticker=False) for r in rs)
        blocks.append(f"""<section class="company-block">
<h2 class="company"><a href="/reports/{ticker}/">{ticker}</a><small>{escape(rs[0]['company'])} · {len(rs)} rapor</small></h2>
<div class="cards">
{cards}
</div>
</section>""")

    latest = reports[:3]
    latest_html = "\n".join(card(r) for r in latest)
    doc = head(
        f"{SITE_NAME} — BIST Bilanço ve Finansal Analiz Raporları",
        "BIST şirketlerinin bilanço, gelir tablosu, nakit akışı ve oran analizleri. "
        "KAP kaynaklı, dönem dönem arşiv.",
        "/",
    )
    doc += header_block() + f"""<main><div class="wrap">
<div class="counters">
<div class="counter"><div class="v">{len(tickers)}</div><div class="k">Şirket</div></div>
<div class="counter"><div class="v">{len(reports)}</div><div class="k">Rapor</div></div>
<div class="counter"><div class="v">{latest[0]['periodLabel'] if latest else '—'}</div><div class="k">En yeni dönem</div></div>
</div>
<div class="controls">
<input id="q" type="search" placeholder="Şirket veya ticker ara (ör. SISE)" aria-label="Şirket ara">
<div class="filters" id="filters">
{''.join(filters)}
</div>
</div>
<h2 class="company">En Yeni Raporlar</h2>
<div class="cards">
{latest_html}
</div>
{''.join(blocks)}
<p class="empty" id="empty" hidden>Eşleşen rapor yok.</p>
</div></main>
""" + footer() + """<script src="/assets/js/site.js" defer></script>
</body></html>
"""
    (ROOT / "index.html").write_text(doc, encoding="utf-8")


def build_company(ticker: str, rs: list[dict]) -> None:
    rs = sort_reports(rs)
    rows = "\n".join(card(r, show_ticker=False) for r in rs)
    company = rs[0]["company"]
    doc = head(
        f"{ticker} — {company} · Rapor Arşivi",
        f"{company} ({ticker}) için yayınlanan tüm finansal analiz raporları: "
        "bilanço, gelir tablosu, nakit akışı ve oran analizleri.",
        f"/reports/{ticker}/",
    )
    doc += header_block() + f"""<main><div class="wrap">
<div class="breadcrumb"><a href="/">Ana Sayfa</a> / {ticker}</div>
<h2 class="company">{ticker}<small>{escape(company)} · {len(rs)} rapor</small></h2>
<div class="cards">
{rows}
</div>
</div></main>
""" + footer() + "</body></html>\n"
    out = ROOT / "reports" / ticker
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(doc, encoding="utf-8")


def build_companies(data: dict) -> None:
    tickers: dict[str, list[dict]] = {}
    for r in data["reports"]:
        tickers.setdefault(r["ticker"], []).append(r)
    for ticker, rs in tickers.items():
        build_company(ticker, rs)


def build_sitemap(data: dict) -> None:
    urls = [(BASE + "/", max((r["updatedAt"] for r in data["reports"]), default=None))]
    tickers = sorted({r["ticker"] for r in data["reports"]})
    for t in tickers:
        urls.append((f"{BASE}/reports/{t}/", None))
    for r in sort_reports(data["reports"]):
        urls.append((BASE + r["path"], r["updatedAt"]))
    items = []
    for loc, lastmod in urls:
        mod = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        items.append(f"  <url><loc>{loc}</loc>{mod}</url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(items)
        + "\n</urlset>\n"
    )
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")


def main() -> None:
    data = load()
    build_index(data)
    build_companies(data)
    build_sitemap(data)
    print(f"OK: {len(data['reports'])} rapor, index + şirket sayfaları + sitemap üretildi")


if __name__ == "__main__":
    main()
