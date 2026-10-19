"""Secovi-SP — Pesquisa Mensal do Mercado Imobiliário (PMI), cidade de São Paulo.

Cada mês tem um PDF em https://secovi.com.br/wp-content/uploads/{ano_pub}/{mes_pub}/{AAAAMM}-pmi.pdf,
publicado ~2 meses após o mês de referência. A página 4 traz um quadro-resumo:
Vendas, VGV, Lançamentos, VGL, Oferta Final, VGO, VSO mensal e VSO 12 meses.
"""
from __future__ import annotations

import datetime as dt
import io
import re

import pdfplumber

from .. import http, store

PDF = "https://secovi.com.br/wp-content/uploads/{py}/{pm:02d}/{ref}-pmi.pdf"
LABELS = [  # rótulo no PDF -> (series_id, nome, unidade)
    ("Vendas", "vendas", "Vendas de unidades residenciais novas", "unidades"),
    ("VGV (INCC)", "vgv", "VGV — valor global de vendas (R$ mi, INCC)", "R$ mi"),
    ("Lançamentos", "lancamentos", "Lançamentos de unidades residenciais", "unidades"),
    ("VGL (INCC)", "vgl", "VGL — valor global lançado (R$ mi, INCC)", "R$ mi"),
    ("Oferta Final", "oferta", "Oferta final (estoque, lançamentos de 36 meses)", "unidades"),
    ("VGO (INCC)", "vgo", "VGO — valor da oferta (R$ mi, INCC)", "R$ mi"),
    ("VSO - mensal", "vso_mensal", "VSO — vendas sobre oferta (mensal)", "%"),
    ("VSO - 12 meses", "vso_12m", "VSO — vendas sobre oferta (12 meses)", "%"),
]
NUM = r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\*{3})"


def _num(s: str) -> float | None:
    if s.startswith("*"):
        return None
    return float(s.replace(".", "").replace(",", "."))


def _months_back(n: int, last: dt.date | None = None):
    last = last or (dt.date.today().replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    y, m = last.year, last.month
    for _ in range(n):
        yield y, m
        m -= 1
        if m == 0:
            y, m = y - 1, 12


def fetch_pdf(y: int, m: int, refresh: bool = False) -> bytes | None:
    """Tenta as pastas de publicação ref+2, ref+1, ref+3 meses."""
    ref = f"{y}{m:02d}"
    for lag in (2, 1, 3):
        pm = m + lag
        py = y + (pm - 1) // 12
        pm = (pm - 1) % 12 + 1
        url = PDF.format(py=py, pm=pm, ref=ref)
        cache = f"secovi/{ref}-pmi.pdf"
        if (http.RAW / cache).exists() and not refresh:
            return http.get(url, cache_name=cache)
        if http.exists(url):
            return http.get(url, cache_name=cache, refresh=True)
    return None


def parse(pdf: bytes) -> dict[str, float]:
    """Lê o quadro-resumo (página 4; procura nas páginas 3-6) e devolve {series_id: valor do mês}."""
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for pg in doc.pages[2:6]:
            text = pg.extract_text() or ""
            if "Oferta Final" in text and "VSO" in text:
                vals = {}
                for label, sid, _, _ in LABELS:
                    m = re.search(re.escape(label) + r"\s*\n?\s*" + NUM, text)
                    if m:
                        v = _num(m.group(1))
                        if v is not None:
                            vals[sid] = v
                if len(vals) >= 4:
                    return vals
    return {}


def collect(months: int = 36, refresh: bool = False):
    out, found = [], []
    for y, m in _months_back(months):
        pdf = fetch_pdf(y, m, refresh)
        if not pdf:
            continue
        vals = parse(pdf)
        if not vals:
            print(f"[secovi] {y}-{m:02d}: PDF encontrado mas quadro-resumo não reconhecido")
            continue
        found.append(f"{y}-{m:02d}")
        for _, sid, name, unit in LABELS:
            if sid in vals:
                out.append(dict(source="secovi", series_id=sid, name=name, block="oferta", region="São Paulo (cidade)",
                                unit=unit, freq="M", date=f"{y}-{m:02d}-01", value=vals[sid]))
    df = store.frame(out)
    store.save(df, "secovi", {"url": "https://secovi.com.br/pesquisa-mensal-do-mercado-imobiliario/",
                              "title": "Secovi-SP — Pesquisa Mensal do Mercado Imobiliário",
                              "coverage": "Cidade de São Paulo, incorporadoras associadas; valores deflacionados pelo INCC-DI",
                              "months_found": sorted(found)})
    return df


if __name__ == "__main__":
    collect()
