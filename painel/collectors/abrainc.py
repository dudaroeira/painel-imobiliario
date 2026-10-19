"""Abrainc-Fipe — Indicadores do mercado primário (lançamentos, vendas, entregas, distratos, oferta).

Amostra: ~20 incorporadoras associadas à Abrainc (viés para grandes empresas e MCMV).
A Abrainc publica a série histórica completa em XLSX (link muda a cada mês); o coletor raspa a
página de indicadores para achar o arquivo 'Series-Historicas-AbraincFipe_AAAAMM.xlsx'.
"""
from __future__ import annotations

import io
import re

import openpyxl
from bs4 import BeautifulSoup

from .. import http, store

PAGE = "https://www.abrainc.org.br/dados-de-mercado/indicadores-publicacoes/indicadores"
FALLBACK = "https://cdn.abrainc.org.br/files/2026/4/Series-Historicas-AbraincFipe_202603.xlsx"

SEGMENT = {"Todos os empreeendimentos": "total", "Todos os empreendimentos": "total",
           "Médio e Alto Padrão (MAP)": "map", "Minha Casa Minha Vida (MCMV) / Programa Casa Verde Amarela (CVA)": "mcmv",
           "Outros empreendimentos ou unidades sem informação": "outros"}
DIM = {"Unidades lançadas": ("lancamentos", "Lançamentos", "unidades"),
       "Unidades vendidas": ("vendas", "Vendas", "unidades"),
       "Unidades entregues": ("entregas", "Entregas", "unidades"),
       "Unidades distratadas": ("distratos", "Distratos", "unidades"),
       "Unidades em oferta": ("oferta", "Oferta final (estoque)", "unidades"),
       "Valor nominal dos lançamentos (milhões R$)": ("vgv_lancamentos_nominal", "VGV lançado (nominal)", "R$ mi"),
       "Valor nominal das vendas \n(milhões R$)": ("vgv_vendas_nominal", "VGV vendido (nominal)", "R$ mi")}


def _find_xlsx(refresh: bool) -> str:
    try:
        html = http.get(PAGE, cache_name="abrainc/indicadores.html", refresh=refresh).decode("utf-8", "ignore")
        links = [a["href"] for a in BeautifulSoup(html, "lxml").select("a[href]") if "Series-Historicas" in a["href"]]
        if links:
            return max(links, key=lambda u: re.findall(r"_(\d{6})", u) or ["0"])
    except Exception as e:
        print(f"[abrainc] não achei link na página: {e}")
    return FALLBACK


def collect(refresh: bool = True):
    url = _find_xlsx(refresh)
    fname = url.rsplit("/", 1)[-1]
    wb = openpyxl.load_workbook(io.BytesIO(http.get(url, cache_name=f"abrainc/{fname}", refresh=refresh)), data_only=True)
    ws = wb["Indicadores Abrainc-Fipe"]
    rows = list(ws.iter_rows(values_only=True))
    hdr_dim = next(r for r in rows if r[0] == "dimensão")
    hdr_ind = next(r for r in rows if r[0] == "indicador")
    # mapeia coluna -> (series_id, nome, unidade, segmento) propagando a dimensão para a direita
    colmap, cur = {}, None
    for i, (d, ind) in enumerate(zip(hdr_dim, hdr_ind)):
        if d:
            cur = d.strip() if isinstance(d, str) else None
        if cur and ind and cur in DIM:
            sid, label, unit = DIM[cur]
            seg = SEGMENT.get(str(ind).strip(), None)
            if seg:
                colmap[i] = (f"{sid}_{seg}", f"{label} — {dict(total='total', map='médio/alto padrão', mcmv='MCMV', outros='outros').get(seg)}", unit)
    out = []
    for r in rows:
        if len(r) > 2 and hasattr(r[2], "year"):
            d = r[2].strftime("%Y-%m-01")
            for i, (sid, name, unit) in colmap.items():
                v = r[i] if i < len(r) else None
                if isinstance(v, (int, float)):
                    out.append(dict(source="abrainc", series_id=sid, name=name, block="oferta", region="BR", unit=unit, freq="M", date=d, value=v))
    df = store.frame(out)
    store.save(df, "abrainc", {"url": url, "title": "Abrainc-Fipe — Indicadores do mercado primário",
                               "coverage": "Brasil, amostra de ~20 incorporadoras associadas (não é censo)"})
    return df


if __name__ == "__main__":
    collect()
