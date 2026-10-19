"""Fipe — Índice FipeZap (preços de oferta de venda e locação, residencial), ~56 cidades.

Planilha com URL fixa, uma aba por cidade; colunas: Venda/Locação × (índice, var. mensal, var. 12m, R$/m²)
× (Total, 1D..4D) + rental yield.
"""
from __future__ import annotations

import io

import openpyxl

from .. import http, store

URL = "https://downloads.fipe.org.br/indices/fipezap/fipezap-serieshistoricas.xlsx"

# (coluna 0-based, series_id, nome, unidade)
COLS = [
    (2, "venda_indice", "FipeZap venda — número-índice", "índice"),
    (12, "venda_var12m", "FipeZap venda — var. 12 meses", "%"),
    (17, "venda_preco_m2", "FipeZap venda — preço médio", "R$/m²"),
    (22, "locacao_indice", "FipeZap locação — número-índice", "índice"),
    (32, "locacao_var12m", "FipeZap locação — var. 12 meses", "%"),
    (37, "locacao_preco_m2", "FipeZap locação — preço médio", "R$/m²"),
    (42, "rental_yield", "FipeZap — rental yield (% a.m.)", "% a.m."),
]
SKIP_SHEETS = {"Resumo", "Aux", "Menu"}


def collect(refresh: bool = True):
    wb = openpyxl.load_workbook(io.BytesIO(http.get(URL, cache_name="fipezap/fipezap-serieshistoricas.xlsx", refresh=refresh)),
                                data_only=True, read_only=True)
    out = []
    for ws in wb.worksheets:
        if ws.title in SKIP_SHEETS:
            continue
        region = "BR" if ws.title.startswith("Índice FipeZAP") else ws.title
        rows = ws.iter_rows(min_row=5, values_only=True)
        for r in rows:
            if r is None or len(r) < 43 or not hasattr(r[1], "year"):
                continue
            for col, sid, name, unit in COLS:
                v = r[col]
                if isinstance(v, (int, float)):
                    if unit.startswith("%"):
                        v = v * 100  # planilha traz fração
                    out.append(dict(source="fipezap", series_id=sid, name=name, block="precos", region=region,
                                    unit=unit, freq="M", date=r[1].strftime("%Y-%m-01"), value=v))
    df = store.frame(out)
    store.save(df, "fipezap", {"url": URL, "title": "Fipe — Índice FipeZap (residencial)",
                               "coverage": "Índice Brasil + cidades monitoradas; preços de OFERTA (anúncios)"})
    return df


if __name__ == "__main__":
    collect()
