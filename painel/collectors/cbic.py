"""CBIC/CII + Brain — Indicadores Imobiliários Nacionais (trimestral, ~220 cidades).

Os PDFs completos ficam atrás de cadastro no Hub de Dados, mas a apresentação da coletiva de
imprensa é publicada aberta em cbic.org.br/wp-content/uploads. Cada apresentação traz tabelas
"por região" com os últimos 9 trimestres de lançamentos, vendas e oferta final; edições mais
novas revisam os trimestres anteriores, então a edição mais recente prevalece.
"""
from __future__ import annotations

import io
import re

import pdfplumber
from bs4 import BeautifulSoup

from .. import http, store

# PDFs públicos conhecidos (a descoberta automática complementa esta lista)
KNOWN = [
    "https://cbic.org.br/wp-content/uploads/2025/05/indppt1t2025-1.pdf",
    "https://cbic.org.br/wp-content/uploads/2026/02/cbic-indppt4t2025vap20fev17h45-1.pdf",
    "https://cbic.org.br/wp-content/uploads/2026/05/indppt1t2026vap25maio17h20.pdf",
    "https://cbic.org.br/wp-content/uploads/2026/08/ind2t2026cbic.pdf",
]
SEARCH = "https://cbic.org.br/page/{page}/?s=indicadores+imobiliarios+nacionais+trimestre"
PDF_RE = re.compile(r"https://cbic\.org\.br/wp-content/uploads/\d{4}/\d{2}/[^\"']*ind[^\"']*\.pdf", re.I)

REGIONS = {"Norte": "Norte", "Nordeste": "Nordeste", "Centro-Oeste": "Centro-Oeste", "Sudeste": "Sudeste", "Sul": "Sul", "TOTAL": "BR"}
METRICS = [  # (texto que identifica a página, series_id, nome)
    ("Unidades residenciais lançadas", "lancamentos", "Lançamentos residenciais (CBIC, ~220 cidades)"),
    ("Unidades residenciais vendidas", "vendas", "Vendas residenciais (CBIC, ~220 cidades)"),
    ("Oferta Final disponível", "oferta", "Oferta final (CBIC, ~220 cidades)"),
]
Q_RE = re.compile(r"\b([1-4])T\s?(\d{4}|\d{2})\b")
INT_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d{1,3})(?![\d.,%])")
# páginas "MCMV x Demais Padrões por trimestre": participação do MCMV em % inteiro, 9 trimestres
QDASH_RE = re.compile(r"\b([1-4])T-(\d{2})\b")
PCT_RE = re.compile(r"(?<![\d,+\-])(\d{1,2})%")
MCMV_PAGES = {"Unidades Lançadas": "lancamentos", "Unidades Vendidas": "vendas", "Unidades em Oferta": "oferta"}


def discover(refresh: bool) -> list[str]:
    urls = set(KNOWN)
    try:
        for page in (1, 2, 3):
            html = http.get(SEARCH.format(page=page), cache_name=f"cbic/search_{page}.html", refresh=refresh).decode("utf-8", "ignore")
            posts = {a["href"] for a in BeautifulSoup(html, "lxml").select("a[href]")
                     if "cbic.org.br/" in a["href"] and re.search(r"trimestre|indicadores-imobiliarios", a["href"]) and "?s=" not in a["href"]}
            for post in sorted(posts):
                slug = post.rstrip("/").rsplit("/", 1)[-1][:80]
                body = http.get(post, cache_name=f"cbic/post_{slug}.html", refresh=refresh).decode("utf-8", "ignore")
                urls.update(PDF_RE.findall(body))
    except Exception as e:
        print(f"[cbic] descoberta parcial: {e}")
    return sorted(urls)


def _quarter_date(q: str, yy: str) -> str:
    year = yy if len(yy) == 4 else "20" + yy
    return f"{year}-{(int(q) - 1) * 3 + 1:02d}-01"


def _parse_mcmv_page(text: str) -> tuple[str, dict, int | None] | None:
    """Página 'MCMV x Demais Padrões por trimestre' -> (metrica, {date: share_mcmv_%}, valor exato do último trimestre)."""
    # a métrica vem do título ("Unidades Vendidas | 2T 2026"); o rodapé "Variação Unidades Lançadas"
    # aparece por engano também na página de vendas, por isso só o trecho antes de "MCMV x Demais" conta
    head = text.split("MCMV x Demais")[0]
    metric = next((sid for key, sid in MCMV_PAGES.items() if key in head), None)
    if not metric:
        return None
    qline = next((ln for ln in text.splitlines() if len(QDASH_RE.findall(ln)) >= 9), None)
    if not qline:
        return None
    quarters = [_quarter_date(q, yy) for q, yy in QDASH_RE.findall(qline)[:9]]
    body = text.split("Variação")[0]  # as linhas de variação trimestral vêm depois e têm % com sinal/decimal
    shares = [int(p) for p in PCT_RE.findall(body)][:9]
    if len(shares) < 9:
        return None
    # o valor absoluto impresso ("MCMV: 48.648") muda de posição entre edições; fica só a participação
    return metric, dict(zip(quarters, shares)), None


def parse(pdf: bytes) -> tuple[dict, str]:
    """Devolve ({(series_id, region, date): valor}, trimestre_mais_recente)."""
    out, latest, mcmv = {}, "", []
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for pg in doc.pages:
            text = pg.extract_text() or ""
            if "Demais Padrões por trimestre" in text:
                r = _parse_mcmv_page(text)
                if r:
                    mcmv.append(r)
                continue
            if "Região" not in text or "TOTAL" not in text:
                continue
            metric = next(((sid, nm) for key, sid, nm in METRICS if key.lower() in text.lower()), None)
            if not metric:
                continue
            # a linha com mais trimestres é o cabeçalho da tabela; depois dos 9 trimestres vêm
            # os pares das colunas de variação ("4T 25 x 1T 26"), que são descartados
            lines = sorted(text.splitlines(), key=lambda ln: -len(Q_RE.findall(ln)))
            quarters = []
            for q, yy in Q_RE.findall(lines[0]):
                d = _quarter_date(q, yy)
                if quarters and d <= quarters[-1]:
                    break
                quarters.append(d)
            if len(quarters) < 4:
                continue
            for ln in text.splitlines():
                name = next((r for r in REGIONS if ln.startswith(r + " ")), None)
                if not name:
                    continue
                nums = [int(n.replace(".", "")) for n in INT_RE.findall(ln)]
                nums = nums[: len(quarters)]
                for d, v in zip(quarters, nums):
                    out[(metric[0], REGIONS[name], d)] = v
                    latest = max(latest, d)
    # MCMV × demais padrões (Brasil): participação publicada em % inteiro × total do trimestre
    for metric, shares, _ in mcmv:
        for d, share in shares.items():
            total = out.get((metric, "BR", d))
            if total is None:
                continue
            v = round(total * share / 100)
            out[(f"{metric}_mcmv", "BR", d)] = v
            out[(f"{metric}_demais", "BR", d)] = total - v
            out[(f"{metric}_mcmv_share", "BR", d)] = v / total * 100
    return out, latest


def collect(refresh: bool = True):
    merged, order = {}, []
    for url in discover(refresh):
        name = url.rsplit("/", 1)[-1]
        try:
            vals, latest = parse(http.get(url, cache_name=f"cbic/{name}", refresh=False))
        except Exception as e:
            print(f"[cbic] {name}: {e}")
            continue
        if vals:
            order.append((latest, name, vals))
    # edições mais antigas primeiro; as novas sobrescrevem trimestres revisados
    for _, name, vals in sorted(order, key=lambda t: t[0]):
        merged.update(vals)
    names = {sid: nm for _, sid, nm in METRICS}
    label = {"lancamentos": "Lançamentos", "vendas": "Vendas", "oferta": "Oferta final"}
    for base, lb in label.items():
        names[f"{base}_mcmv"] = f"{lb} — MCMV (CBIC)"
        names[f"{base}_demais"] = f"{lb} — demais padrões (CBIC)"
        names[f"{base}_mcmv_share"] = f"{lb} — participação do MCMV (CBIC)"
    rows = [dict(source="cbic", series_id=sid, name=names[sid], block="oferta", region=reg,
                 unit="%" if sid.endswith("_share") else "unidades", freq="Q", date=d, value=v)
            for (sid, reg, d), v in merged.items()]
    df = store.frame(rows)
    store.save(df, "cbic", {"url": "https://cbic.org.br/hubdedados/mercado", "title": "CBIC/CII — Indicadores Imobiliários Nacionais",
                            "coverage": "~220 cidades (capitais, RMs e interior), residencial, trimestral; apresentações públicas das coletivas",
                            "pdfs": [n for _, n, _ in sorted(order, key=lambda t: t[0])]})
    return df


if __name__ == "__main__":
    collect()
