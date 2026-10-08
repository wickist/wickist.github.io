#!/usr/bin/env python3
"""Yayın öncesi doğrulama kapısı (§16). Hata varsa exit != 0 — push YAPILMAZ.

Kullanım: python3 tools/validate_site.py
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://wickist.github.io"
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in {"meta", "link", "br", "img", "hr", "input", "path", "rect",
                       "circle", "line", "polyline", "polygon", "use", "stop", "source"}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()


def parse_ok(path: Path) -> None:
    try:
        p = Parser()
        p.feed(path.read_text(encoding="utf-8"))
        if p.stack:
            err(f"{path}: kapanmamış etiketler {p.stack[:5]}")
    except Exception as exc:  # noqa: BLE001
        err(f"{path}: parse hatası {exc}")


def check_meta(path: Path, *, report: bool, social: bool = True) -> None:
    head = path.read_text(encoding="utf-8")[:12000]
    required = [
        (r"<title>[^<]{5,}</title>", "title"),
        (r'<meta name="description" content="[^"]{10,}"', "description"),
        (r'<link rel="canonical" href="https://', "canonical"),
        (r'<meta property="og:title" content="', "og:title"),
        (r'<meta property="og:description" content="', "og:description"),
        (r'<meta property="og:url" content="https://wickist\.github\.io/', "og:url"),
        (r'<meta property="og:image" content="https://wickist\.github\.io/[^"]+', "og:image"),
        (r'<meta name="twitter:card" content="summary_large_image"', "twitter:card"),
        (r'<meta name="twitter:image" content="https://wickist\.github\.io/[^"]+', "twitter:image"),
        (r'<html lang="tr"', "lang=tr"),
        (r'charset="UTF-8"', "utf-8"),
        (r'name="viewport"', "viewport"),
    ]
    if not social:
        required = [req for req in required if req[1] not in
                    {"canonical", "og:title", "og:description", "og:url",
                     "og:image", "twitter:card", "twitter:image"}]
    if "DOMAIN" in head or "USERNAME" in head:
        err(f"{path}: placeholder (DOMAIN/USERNAME) içeriyor")
    for pattern, name in required:
        if not re.search(pattern, head):
            err(f"{path}: eksik/geçersiz {name}")
    if report and "yatırım tavsiyesi değildir" not in path.read_text(encoding="utf-8"):
        err(f"{path}: yatırım tavsiyesi uyarısı yok")


def main() -> None:
    reg_path = ROOT / "data" / "reports.json"
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        err(f"reports.json geçersiz JSON: {exc}")
        print("\n".join(errors))
        sys.exit(1)

    seen = set()
    for r in reg["reports"]:
        key = (r["ticker"], r["period"])
        if key in seen:
            err(f"duplicate ticker+period: {key}")
        seen.add(key)
        rep = ROOT / r["path"].strip("/") / "index.html"
        if not rep.is_file():
            err(f"rapor dosyası yok: {rep}")
            continue
        parse_ok(rep)
        check_meta(rep, report=True)
        cover = ROOT / r["ogImage"].lstrip("/")
        if not cover.is_file():
            err(f"og-cover yok: {cover}")
        elif cover.suffix == ".svg":
            err("og:image SVG olamaz")

    for page in ("index.html", "404.html"):
        p = ROOT / page
        if not p.is_file():
            err(f"{page} yok")
            continue
        parse_ok(p)
        # 404 noindex'tır; sosyal/canonical zorunluluğu uygulanmaz
        check_meta(p, report=False, social=page == "index.html")

    # dahili bağlantı çözünürlüğü
    for html_path in ROOT.rglob("*.html"):
        for href in re.findall(r'href="(/[^"#][^"]*)"', html_path.read_text(encoding="utf-8")):
            target = ROOT / href.split("?")[0].lstrip("/")
            if not (target.exists() or (target / "index.html").is_file()):
                err(f"{html_path.relative_to(ROOT)}: kırık dahili link {href}")
        for src in re.findall(r'src="(/[^"]*)"', html_path.read_text(encoding="utf-8")):
            if not (ROOT / src.split("?")[0].lstrip("/")).is_file():
                err(f"{html_path.relative_to(ROOT)}: kırık asset {src}")

    # sitemap: kayıtlı URL'ler üretilmiş mi, silinmiş URL kalmamış mı
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.is_file():
        err("sitemap.xml yok")
    else:
        xml = sitemap.read_text(encoding="utf-8")
        for r in reg["reports"]:
            if BASE + r["path"] not in xml:
                err(f"sitemap'te eksik: {r['path']}")
        for loc in re.findall(r"<loc>([^<]+)</loc>", xml):
            p = urlparse(loc).path
            t = ROOT / p.strip("/")
            if not (t.exists() or (t / "index.html").is_file()):
                err(f"sitemap ölü URL: {loc}")

    if not (ROOT / ".nojekyll").is_file():
        err(".nojekyll yok")
    if not (ROOT / "robots.txt").is_file():
        err("robots.txt yok")
    fb = ROOT / "assets/images/site-og.png"
    if not fb.is_file():
        err("site-og.png fallback yok")

    if errors:
        print("FAIL:")
        print("\n".join(" - " + e for e in errors))
        sys.exit(1)
    print(f"PASS: {len(reg['reports'])} rapor + portal + sitemap doğrulandı")


if __name__ == "__main__":
    main()
