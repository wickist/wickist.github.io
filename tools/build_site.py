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
ASSET_VER = "20261008a"   # site.css değişince artır (cache-busting)


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
<link rel="stylesheet" href="/assets/css/site.css?v={ASSET_VER}">
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

    # Dönem kolonları (yeni->eski) ve şirket×dönem matrisi
    period_keys: dict[tuple[int, int], str] = {}
    for r in reports:
        period_keys.setdefault((r["year"], r["quarter"]), r["periodLabel"])
    cols = sorted(period_keys, reverse=True)

    rows = []
    for ticker in sorted(tickers):
        rs = tickers[ticker]
        search = f"{ticker} {rs[0]['company']}".lower()
        cells = []
        for key in cols:
            hit = next((r for r in rs if (r["year"], r["quarter"]) == key), None)
            if hit:
                cells.append(
                    f'<td><a class="chip" href="{escape(hit["path"])}" '
                    f'data-year="{hit["year"]}" data-quarter="{hit["quarter"]}" '
                    f'title="{escape(hit["title"])}">{escape(hit["periodLabel"])}</a></td>'
                )
            else:
                cells.append('<td><span class="none">—</span></td>')
        rows.append(
            f'<tr class="arow" data-search="{escape(search)}">'
            f'<th scope="row"><a href="/reports/{ticker}/">{ticker}</a>'
            f'<br><small>{escape(rs[0]["company"])}</small></th>'
            + "".join(cells) +
            f'<td class="cnt">{len(rs)}</td></tr>'
        )
    thead = '<tr><th>Şirket</th>' + "".join(
        f'<th>{escape(period_keys[k])}</th>' for k in cols) + '<th>N</th></tr>'
    archive = f"""<section class="arsiv">
<h2 class="company">Şirket Arşivi</h2>
<div class="tblwrap"><table class="arsiv">
<thead>{thead}</thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table></div>
</section>"""

    latest = reports[:6]
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
{archive}
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
