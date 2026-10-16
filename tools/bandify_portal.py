#!/usr/bin/env python3
"""Portal kopyalarına AL/SAT/TUT → renk-bandı + hero/başlık dönüşümlerini uygular.

KURAL (kullanıcı): dönüşümler YALNIZ portal sürümüne; yerel reports/*.html değişmez.
inject_report.py yereli birebir taşıdığı için enjeksiyondan SONRA her seferinde
koşulmalıdır (aksi halde eski uyumlu yayın 21dd8b5 türü rejrese girer).

Kullanım: python3 tools/bandify_portal.py [--ticker T ...]   (varsayılan: kayıtlı 16'sı)
Her değiştirme tam-esnek + beklenen-tekilassert'u ile koşar; sapma varsa dosya YAZILMAZ.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = re.compile(r"(?<![A-Za-zÀ-ÿçğıöşüÇĞİÖŞÜ])(AL|SAT|TUT)(?![A-Za-zÀ-ÿçğıöşüÇĞİÖŞÜ])")
BAND_CSS = ("\n.band{display:inline-block;width:46px;height:14px;border-radius:7px;"
            "vertical-align:middle;background:#6A8E7F}\n"
            ".band.red{background:#B0472A}\n"
            ".band.gray{background:#9A958A}\n")
GREEN = '<span class="band"></span>'
RED = '<span class="band red"></span>'
GRAY = '<span class="band gray"></span>'

# ---- global dönüşümler (her dosya) ----
HERO_KARAR = re.compile(r" ?Karar: <b>[^<]*</b>\.")
H2_ONERI = re.compile(r"(<h2[^>]*>)((?:\d+\s*[·.]\s*)?)Öneri[^<]*(</h2>)")

# ---- ticker-özgün tam eşleşme listesi ----
EDITS: dict[str, list[tuple[str, str]]] = {
    "AAGYO": [
        ('<span class="badge hold">İZLE — "ucuz GYO" sepetine alınmaz; üç tetikleyicinin ikisi pozitife dönmeli</span>',
         '<span class="badge hold">Portföy getirisi defteri taşımıyor; üç tetikleyicinin ikisi pozitife dönmeli</span>'),
        ('<b>Karar: İZLE — "ucuz GYO" sepetine alınmaz.</b>',
         '<b>Karar: İZLE — "ucuz GYO" sepeti gerekçesi taşımıyor.</b>'),
        ('<td>elde tut; "ucuz" sepetine alma</td>', '<td>izleme listesinde tutulur</td>'),
        ('<td>kademeli kâr realizasyonu</td>', '<td>pozisyon gözden geçirilir</td>'),
    ],
    "AFYON": [
        ('<div class="kararband"><span class="kchip">AL</span><span class="kchip">SAT</span><span class="kchip">TUT</span><span class="kchip on izle">İZLE</span></div>',
         '<div class="kararband"><span class="kchip on izle">İZLE</span></div>'),
        ('7 · Hüküm ve öneri</h2>', '7 · Öneri ve gerekçe</h2>'),
        ('opsiyon değerli. Karar: İZLE.', 'opsiyon değerli. Karar: <b>İZLE</b>.'),
        ('<span class="badge hold">İZLE</span>', '<span class="badge hold">Varlık iskontosu izleniyor</span>'),
        ("<b>AL'a terfi eşikleri:</b>", '<b>Yükseltme eşikleri:</b>'),
        ('Ama üç şey birlikte "al" dedirtmiyor:', 'Ama üç şey birlikte yükseltme sinyali vermiyor:'),
    ],
    "AGROT": [
        ('AL için erken; SAT için varlık gerekçesi yok.',
         f'{GREEN} için erken; {RED} için varlık gerekçesi yok.'),
        ('<td>Alım yok — tez-eşikleri beklenir</td>',
         '<td>izleme listesinde tutulur — tez-eşikleri beklenir</td>'),
        ('<span class="badge hold">İZLE (spekülatif) — alım yok: tez-eşikleri beklenir</span>',
         '<span class="badge hold">İZLE (spekülatif) — tez-eşikleri beklenir</span>'),
        ('<td>Kademeli giriş savunulabilir</td>', '<td>tetikler oluşursa model yeniden koşar</td>'),
        ('<td>Pozisyon/alım gözden geçirilir</td>', '<td>pozisyon gözden geçirilir</td>'),
    ],
    "ASELS": [
        ('<span class="badge">İZLE (negatif eğilimli) — güvenlik marjı yok; pozisyon sektör çarpanı pozisyonudur</span>',
         '<span class="badge">Güvenlik marjı yok; fiyat sektör çarpanı düzeyinde</span>'),
        ('<li><b>Alım önerilmez.</b>', '<li><b>Güvenlik marjı yok.</b>'),
        ('bandın içinde; güvenlik marjı yok.</li>', 'bandın içinde; iskontolu bölge değil.</li>'),
    ],
    "BERA": [
        ('<span class="badge hold">İZLE — holding iskontosu',
         '<span class="badge hold">Holding iskontosu'),
        ('<td>sepete alma; izlemeye al</td>', '<td>izleme listesinde tutulur</td>'),
        ('<td>kademeli giriş savunulabilir</td>', '<td>tetikler oluşursa model yeniden koşar</td>'),
    ],
    "CVKMD": [
        ('<span class="badge hold">TUT — çarpan tam, marj kanıtı bekliyor</span>',
         '<span class="badge hold">Çarpan tam; marj kanıtı bekliyor</span>'),
        ('<b>AL eşiği:</b>', f'<b>{GREEN} eşiği:</b>'),
        ('<b>SAT eşiği:</b>', f'<b>{RED} eşiği:</b>'),
        ('<b>Eşik kontrolü:</b> AL eşiği oluşmadı', f'<b>Eşik kontrolü:</b> {GREEN} eşiği oluşmadı'),
        ('; SAT tetikleri (', f'; {RED} tetikleri ('),
    ],
    "DOHOL": [
        ('<span class="badge">AL (kademeli) — fiyat bant alt sınırının %26 altında</span>',
         '<span class="badge">Fiyat, değer bandı alt sınırının %26 altında</span>'),
        ('<b>Hüküm: AL (kademeli).</b>', f'<b>Hüküm: {GREEN} (kademeli).</b>'),
        ('Giriş kademeli.', 'Yakınsama kademeli işler.'),
        ('<td><b>AL</b></td><td>18,37 TL (bant alt sınırının %26 altında)</td><td>İlk tranş; 21 TL altı kademeli ekleme</td>',
         f'<td>{GREEN}</td><td>18,37 TL (bant alt sınırının %26 altında)</td><td>21 TL altı bölge izlenir</td>'),
        ('Karar: <b>AL (kademeli)</b>, band 24,7–25,3 TL.',
         f'Karar: <b>{GREEN} (kademeli)</b>, band 24,7–25,3 TL.'),
    ],
    "EKGYO": [
        ('<span class="badge">AL (kademeli) — fiyat bandın %12 altında</span>',
         '<span class="badge">Fiyat, değer bandının %12 altında</span>'),
        ('AL tezinin zamanlayıcısı', 'giriş tezinin zamanlayıcısı'),
        ('<b>Hüküm: AL (kademeli).</b>', f'<b>Hüküm: {GREEN} (kademeli).</b>'),
        ('<td><b>AL</b></td><td>19,42 TL (bandın %12 altında)</td><td>İlk tranş; 22 TL altı kademeli ekleme</td>',
         f'<td>{GREEN}</td><td>19,42 TL (bandın %12 altında)</td><td>22 TL altı bölge izlenir</td>'),
        ('Giriş kademeli; tetik listesi geçersiz kılarsa pozisyon kesilir.',
         'Tetik listesi izlenir; tetikler geçersiz kılarsa senaryo yeniden koşulur.'),
    ],
    "EREGL": [
        ('<span class="badge hold">İZLE — bilanço fiyatı savunuyor',
         '<span class="badge hold">Bilanço fiyatı savunuyor'),
        ('<td>izleme listesinde tut; alım yok</td>', '<td>izleme listesinde tutulur</td>'),
        ('<td>eşzamanlı teyitte kademeli giriş savunulabilir</td>',
         '<td>tetikler oluşursa model yeniden koşar</td>'),
    ],
    "GWIND": [
        ('<span class="badge">KADEMELİ AL — fiyat bandın %19–34 altında, iskonto tek seferlik</span>',
         '<span class="badge">Fiyat, değer bandının %19–34 altında; iskonto tek seferlik</span>'),
        ('<span class="badge">KADEMELİ AL — hedef bandı 24–30 TL · taban 23,5</span>',
         '<span class="badge">Hedef bandı 24–30 TL · taban 23,5</span>'),
        ('<b>Karar: kademeli alım</b>', '<b>Karar: değer bandı altı bölge izleniyor</b>'),
    ],
    "LIDER": [
        ('<span class="badge hold">İZLE — defter ölçülemiyor',
         '<span class="badge hold">Defter ölçülemiyor'),
        ('<td>sepete alma; izlemeye al</td>', '<td>izleme listesinde tutulur</td>'),
        ('<td>kademeli giriş savunulabilir</td>', '<td>tetikler oluşursa model yeniden koşar</td>'),
    ],
    "SAHOL": [
        ('<span class="badge">İZLE — fiyat iki yöntemin de altında',
         '<span class="badge">Fiyat iki yöntemin de altında'),
    ],
    "SASA": [
        ('<span class="badge warn">SAT — fiyat bant üst sınırının %14 üzerinde (1,94 ↔ bant 0,2–1,7)</span>',
         '<span class="badge warn">Fiyat, bant üst sınırının %14 üzerinde (1,94 ↔ bant 0,2–1,7)</span>'),
        ('<p><span class="badge warn">SAT / yeni pozisyon almaya hayır</span></p>',
         f'<p><span class="badge warn"><span class="band red" style="background:#fff;opacity:.95"></span></span></p>'),
        ('<td><b>SAT / KAÇIN</b></td>', f'<td>{RED}</td>'),
        ('<td>Pozisyon kapatılır; yeni giriş yok</td>', '<td>pozisyon gözden geçirilir</td>'),
    ],
    "SISE": [
        ('<span class="badge hold">İZLE (negatif eğilimli) — yeni giriş yok; karar Q3 FAVÖK okumasına bağlı</span>',
         '<span class="badge hold">Karar Q3 FAVÖK okumasına bağlı — negatif eğilim sürüyor</span>'),
        ('37,32\'de (07.10 canlı) yeni giriş yok: orta döngü', '37,32\'de (07.10 canlı) orta döngü'),
        ('<td>Giriş yok; elde tutanlar için pozisyon Q3 teyidine kadar</td>',
         '<td>Q3 teyidine kadar izlenir</td>'),
    ],
    "THYAO": [
        ('<b>İZLE → AL:</b>', f'<b>İZLE → {GREEN}:</b>'),
        ('<b>İZLE → SAT:</b>', f'<b>İZLE → {RED}:</b>'),
        ('<td>Alım yok; izleme listesinde tut.</td>', '<td>İzleme listesinde tutulur.</td>'),
    ],
    "TRGYO": [
        ('<span class="badge hold">TUT — 88 TL altında kademeli alım; 88–108 bandı yeni pozisyon yok</span>',
         '<span class="badge hold">Fiyat 88–108 TL değer bandı içinde; 88 TL altı iskonto bölgesi izlenir</span>'),
        ('<b>Karar: TUT — 88 TL altında kademeli AL.</b>',
         f'<b>Karar: {GRAY} — 88 TL altı iskonto bölgesi izlenir.</b>'),
        ('<tr><td><b>AL</b></td><td>≤ 88 TL (iskonto ≥ %43)</td><td>kademeli alım</td>',
         f'<tr><td>{GREEN}</td><td>≤ 88 TL (iskonto ≥ %43)</td><td>88 TL altı bölge izlenir</td>'),
        ('<tr><td>TUT</td><td>88 – 108 TL</td><td>elde tut; yeni pozisyon yok</td>',
         f'<tr><td>{GRAY}</td><td>88 – 108 TL</td><td>değer bandı içi — izleme</td>'),
        ('<td>kâr realizasyonu</td>', '<td>pozisyon gözden geçirilir</td>'),
    ],
    "TUPRS": [
        ('<b>İZLE → AL (üçü birlikte):</b>', f'<b>İZLE → {GREEN} (üçü birlikte):</b>'),
        ('<b>İZLE → SAT:</b>', f'<b>İZLE → {RED}:</b>'),
        ('<td>izleme listesinde tut; alım yok</td>', '<td>izleme listesinde tutulur</td>'),
        ('<td>kademeli giriş savunulabilir</td>', '<td>tetikler oluşursa model yeniden koşar</td>'),
    ],
    "YYAPI": [
        ('<span class="badge warn">KAÇIN — yatırım değil; en fazla %1 ağırlıklı spekülatif deneme</span>',
         '<span class="badge warn">Risk: aktarım/tahsilat/likidite — yatırım niteliği düşük</span>'),
        ('<b>Karar: KAÇIN — yatırım değil, en fazla %1 ağırlıklı spekülatif deneme.</b>',
         '<b>Karar: KAÇIN — aktarım/tahsilat/likidite riski; yatırım niteliği düşük.</b>'),
        ('<td>yalnız kayba tahammüllü sermaye, ≤%1 pozisyon</td>',
         '<td>kayba tahammüllü sermaye çerçevesi</td>'),
        ('<td>pozisyon kapat</td>', '<td>pozisyon gözden geçirilir</td>'),
        ('<td>kademeli çıkış</td>', '<td>çıkış senaryosu izlenir</td>'),
    ],
}

ALL = sorted(set(EDITS) | {"EREGL", "TUPRS", "THYAO", "SAHOL", "ASELS", "EKGYO",
                           "DOHOL", "SASA", "SISE"})


def bandify(t: str) -> tuple[str, int]:
    path = ROOT / "reports" / t / "2026-Q2" / "index.html"
    if not path.exists():
        raise SystemExit(f"yok: {path}")
    html = path.read_text(encoding="utf-8")
    n = 0
    for old, new in EDITS.get(t, []):
        c = html.count(old)
        if c != 1:
            raise SystemExit(f"{t}: beklenen 1, bulunan {c}: {old[:70]!r}")
        html = html.replace(old, new)
        n += 1
    # hero "Karar: <b>…</b>." cümlesi (hero/lede'de tek olmalı; gövdedeki "<b>Karar:" biçimine dokunmaz)
    html, k = HERO_KARAR.subn("", html)
    if k < 1:
        raise SystemExit(f"{t}: hero Karar cümlesi bulunamadı")
    n += k
    # "Öneri…" başlığı → "Karar Tablosu" (numara + id + nav etiketi korunur)
    html, k = H2_ONERI.subn(r"\1\2Karar Tablosu\3", html)
    if k != 1:
        raise SystemExit(f"{t}: Öneri başlığı {k} bulundu, 1 bekleniyordu")
    n += k
    if '<span class="band' in html and ".band{" not in html:
        html = html.replace("</style>", BAND_CSS + "</style>", 1)
        n += 1
    m = FORBIDDEN.findall(html)
    if m:
        raise SystemExit(f"{t}: yasak kelime kaldı: {m[:5]}")
    path.write_text(html, encoding="utf-8")
    return html, n


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", action="append", dest="tickers")
    args = p.parse_args()
    tickers = args.tickers or ALL
    for t in tickers:
        _, n = bandify(t.upper())
        print(f"OK {t.upper()}: {n} dönüşüm, tarama=0")


if __name__ == "__main__":
    main()
