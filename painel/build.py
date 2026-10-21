"""Gera dashboard/index.html (página estática, sem servidor) a partir de data/series/*.csv.

Uso: python -m painel.build
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

from . import store

OUT = store.ROOT / "dashboard" / "index.html"
TEMPLATE = Path(__file__).with_name("template.html")

# Séries levadas para o HTML (as demais ficam só no CSV). region=None => todas as regiões.
SELECT = {
    "bcb_olinda": {
        "credito_contratacao_contratado_pf_sfh": None, "credito_contratacao_contratado_pf_fgts": None,
        "credito_contratacao_contratado_pf_livre": None, "credito_contratacao_contratado_pf_home_equity": None,
        "credito_contratacao_contratado_pj_sfh": None, "credito_contratacao_contratado_pj_fgts": None,
        "credito_contratacao_contratado_pj_livre": None,
        "credito_contratacao_taxa_pf_sfh": None, "credito_contratacao_taxa_pf_fgts": None, "credito_contratacao_taxa_pf_livre": None,
        "credito_contratacao_ltv_pf_sfh": None, "credito_contratacao_ltv_pf_fgts": None, "credito_contratacao_ltv_pf_livre": None,
        "credito_contratacao_indexador_pf_tr": None, "credito_contratacao_indexador_pf_ipca": None,
        "credito_contratacao_indexador_pf_prefixado": None, "credito_contratacao_indexador_pf_outros": None,
        "credito_estoque_carteira_credito_pf_sfh": None, "credito_estoque_carteira_credito_pf_fgts": None,
        "credito_estoque_carteira_credito_pf_livre": None, "credito_estoque_carteira_credito_pf_home_equity": None,
        "credito_estoque_inadimplencia_pf_sfh": None, "credito_estoque_inadimplencia_pf_fgts": None,
        "credito_estoque_inadimplencia_pf_livre": None, "credito_estoque_inadimplencia_pf_home_equity": None,
        "credito_estoque_parcela_pf_sfh": None, "credito_estoque_parcela_pf_fgts": None,
        "fontes_sbpe_saldo": ["BR"], "fontes_lci": ["BR"], "fontes_lig": ["BR"], "fontes_cri": ["BR"],
        "direcionamento_aplicacao_imobiliario": ["BR"], "direcionamento_aquisicao_imobiliario": ["BR"],
        "direcionamento_construcao_imobiliario": ["BR"],
        "indices_ivg_r": ["BR"], "indices_mvg_r": ["BR"],
        "imoveis_valor_avaliacao": None, "imoveis_valor_compra": None, "imoveis_area_privativa": None,
        "imoveis_tipo_apartamento": None, "imoveis_tipo_casa": None,
        "imoveis_dormitorio_1": None, "imoveis_dormitorio_2": None, "imoveis_dormitorio_3": None, "imoveis_dormitorio_4_mais": None,
    },
    "bcb_sgs": {"selic_meta_m": ["BR"], "ipca_12m": ["BR"], "ipca": ["BR"], "incc_di": ["BR"], "tr_m": ["BR"], "desemprego": ["BR"],
                "poupanca_saldo_total": ["BR"], "ibc_br": ["BR"]},
    "sidra": {"sinapi_custo_m2": None, "sinapi_custo_m2_var12m": ["BR"], "pib_construcao_var_aa": ["BR"], "pib_total_var_aa": ["BR"]},
    "abecip": {"sbpe_unid_total": ["BR"], "sbpe_unid_construcao": ["BR"], "sbpe_unid_aquisicao": ["BR"],
               "sbpe_rs_total": ["BR"], "igmi_r": None},
    "abrainc": None,  # todas
    "secovi": None,
    "cbic": None,
    "b3": None,
}
START = "2012-01-01"


def select(df: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for src, spec in SELECT.items():
        d = df[df.source == src]
        if spec is None:
            parts.append(d)
            continue
        for sid, regions in spec.items():
            x = d[d.series_id == sid]
            if regions:
                x = x[x.region.isin(regions)]
            parts.append(x)
    out = pd.concat(parts)
    return out[out.date >= START]


def pack(df: pd.DataFrame) -> dict:
    """{source: {series_id: {meta..., regions: {region: [[date, value], ...]}}}}"""
    data = {}
    for (src, sid), g in df.groupby(["source", "series_id"]):
        first = g.iloc[0]
        entry = {"name": first["name"], "block": first["block"], "unit": first["unit"], "freq": first["freq"], "regions": {}}
        for reg, gg in g.groupby("region"):
            gg = gg.sort_values("date")
            entry["regions"][reg] = [[d[:7], round(float(v), 6)] for d, v in zip(gg["date"], gg["value"])]
        data.setdefault(src, {})[sid] = entry
    return data


def main():
    df = store.load_all()
    sel = select(df)
    payload = {
        "built_at": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
        # só fontes do painel: no CI o cache pode restaurar metadados de fontes já retiradas
        "meta": {k: v for k, v in store.load_meta().items() if k in SELECT},
        "data": pack(sel),
    }
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"dashboard: {OUT} ({OUT.stat().st_size / 1e6:.1f} MB, {len(sel):,} pontos, {sel.groupby(['source', 'series_id']).ngroups} séries)")
    export_bi(sel)


# CSVs em formato longo publicados junto com o site (dashboard/data/), para BI externo (Looker Studio etc.)
BI_FILES = {
    # crédito por UF dividido por família para manter cada arquivo pequeno (IMPORTDATA do Google Sheets)
    "credito_contratado": lambda d: d[(d.source == "bcb_olinda") & d.series_id.str.startswith("credito_contratacao_contratado")],
    "credito_taxa_ltv": lambda d: d[(d.source == "bcb_olinda") & (d.series_id.str.startswith("credito_contratacao_taxa") | d.series_id.str.startswith("credito_contratacao_ltv"))],
    "credito_indexador": lambda d: d[(d.source == "bcb_olinda") & d.series_id.str.startswith("credito_contratacao_indexador")],
    "credito_carteira": lambda d: d[(d.source == "bcb_olinda") & (d.series_id.str.startswith("credito_estoque_carteira") | d.series_id.str.startswith("credito_estoque_parcela"))],
    "credito_inadimplencia": lambda d: d[(d.source == "bcb_olinda") & d.series_id.str.startswith("credito_estoque_inadimplencia")],
    "funding": lambda d: d[(d.block == "funding")],
    "oferta_cbic": lambda d: d[d.source == "cbic"],
    "oferta_amostras": lambda d: d[d.source.isin(["abrainc", "secovi"])],
    "precos": lambda d: d[(d.block == "precos") | (d.series_id.isin(["indices_ivg_r", "indices_mvg_r"]))],
    "imoveis": lambda d: d[d.block == "imoveis"],
    "macro_custos": lambda d: d[d.source.isin(["bcb_sgs", "sidra"]) | (d.block == "macro")],
}


def export_bi(df: pd.DataFrame):
    out = OUT.parent / "data"
    out.mkdir(exist_ok=True)
    index = []
    for name, pick in BI_FILES.items():
        part = pick(df).copy()
        part["date"] = part["date"].str[:10]
        # date_key (AAAAMMDD, inteiro): o Looker Studio lê como Data sem depender da formatação da planilha
        part["date_key"] = part["date"].str.replace("-", "").astype(int)
        cols = ["source", "series_id", "name", "region", "unit", "freq", "date", "date_key", "value"]
        part[cols].to_csv(out / f"{name}.csv", index=False, encoding="utf-8")
        index.append({"file": f"{name}.csv", "rows": int(len(part)), "series": int(part.series_id.nunique()),
                      "first": part.date.min() if len(part) else None, "last": part.date.max() if len(part) else None})
    (out / "index.json").write_text(json.dumps({"built_at": dt.datetime.now().isoformat(timespec="minutes"), "files": index},
                                               ensure_ascii=False, indent=1), encoding="utf-8")
    print("BI: " + ", ".join(f"{i['file']} ({i['rows']:,})" for i in index))


if __name__ == "__main__":
    main()
