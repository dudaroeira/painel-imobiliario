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
    # versão enxuta para o Google Sheets / Looker Studio (IMPORTDATA recusa arquivos grandes):
    # colunas em português, rótulo curto da série, nome da região, nível geográfico e mês (AAAAMM01)
    lite = out / "sheets"
    lite.mkdir(exist_ok=True)
    sizes = {}
    for name, pick in BI_FILES.items():
        part = pick(df).copy()
        part["serie"] = [serie_label(s, i, n) for s, i, n in zip(part["source"], part["series_id"], part["name"])]
        part["regiao"] = part["region"].map(lambda r: UF_NAMES.get(r, r))
        part["nivel"] = [nivel(src, r) for src, r in zip(part["source"], part["region"])]
        part["mes"] = (part["date"].str[:7].str.replace("-", "") + "01").astype(int)  # AAAAMMDD, dia 1: o Looker lê como Data
        # R$ grandes sem centavos; demais com até 4 casas
        big = part["value"].abs() >= 1e5
        part["valor"] = part["value"].round(4)
        part.loc[big, "valor"] = part.loc[big, "value"].round(0)
        dup = part.drop_duplicates(["source", "series_id"]).groupby("serie").size()
        assert (dup == 1).all(), f"rótulos repetidos em {name}: {list(dup[dup > 1].index)}"
        p = lite / f"{name}.csv"
        part[["serie", "regiao", "nivel", "mes", "valor"]].to_csv(p, index=False, encoding="utf-8", float_format="%.10g")
        sizes[name] = p.stat().st_size
    d = df.drop_duplicates(["source", "series_id"]).copy()
    d["serie"] = [serie_label(s, i, n) for s, i, n in zip(d["source"], d["series_id"], d["name"])]
    d[["source", "series_id", "serie", "name", "block", "unit", "freq"]].to_csv(lite / "series.csv", index=False, encoding="utf-8")
    kpis(df).to_csv(lite / "indicadores.csv", index=False, encoding="utf-8", float_format="%.10g")
    print("Sheets: " + ", ".join(f"{k} ({v/1e3:.0f} KB)" for k, v in sizes.items()))


UF_NAMES = {"BR": "Brasil", "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
            "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais",
            "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí",
            "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima",
            "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins"}
MACRORREGIOES = {"Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"}


def nivel(source: str, region: str) -> str:
    if region == "BR":
        return "Brasil"
    if region in UF_NAMES:
        return "UF"
    if region in MACRORREGIOES:
        return "Região"
    if source == "abecip":
        return "Capital"
    return "Cidade"


FONTE_RECURSO = {"sfh": "SFH/SBPE", "fgts": "FGTS", "livre": "Taxa de mercado", "home_equity": "Home equity"}
SERIE_LABELS = {
    "direcionamento_aplicacao_imobiliario": "Direcionamento · aplicação imobiliária",
    "direcionamento_aquisicao_imobiliario": "Direcionamento · aquisição",
    "direcionamento_construcao_imobiliario": "Direcionamento · construção",
    "indices_ivg_r": "IVG-R (BCB)", "indices_mvg_r": "MVG-R (BCB)",
    "imoveis_valor_avaliacao": "Valor de avaliação (R$)", "imoveis_valor_compra": "Valor de compra (R$)",
    "imoveis_area_privativa": "Área privativa (m²)", "imoveis_tipo_apartamento": "Apartamentos (unid.)",
    "imoveis_tipo_casa": "Casas (unid.)", "imoveis_dormitorio_1": "1 dormitório (unid.)",
    "imoveis_dormitorio_2": "2 dormitórios (unid.)", "imoveis_dormitorio_3": "3 dormitórios (unid.)",
    "imoveis_dormitorio_4_mais": "4 ou mais dormitórios (unid.)",
    "igmi_r": "IGMI-R (jan/2014 = 100)", "sinapi_custo_m2": "SINAPI · custo por m² (R$)",
}


def serie_label(source: str, sid: str, name: str) -> str:
    """Rótulo curto em português, único dentro de cada aba da planilha."""
    if sid in SERIE_LABELS:
        return SERIE_LABELS[sid]
    if source == "bcb_olinda" and sid.startswith("credito_"):
        tail = sid.rsplit("_pf_", 1)[-1] if "_pf_" in sid else sid.rsplit("_pj_", 1)[-1]
        fonte = FONTE_RECURSO.get(tail, tail.upper() if len(tail) <= 4 else tail.capitalize())
        pessoa = "PJ" if "_pj_" in sid else "PF"
        if "_contratado_" in sid:
            return f"{pessoa} · {fonte}"
        if "_taxa_" in sid:
            return f"Taxa · {fonte}"
        if "_ltv_" in sid:
            return f"LTV · {fonte}"
        if "_indexador_" in sid:
            return {"tr": "TR", "ipca": "IPCA", "prefixado": "Prefixado", "outros": "Outros"}.get(tail, tail)
        if "_carteira_" in sid:
            return f"Saldo · {fonte}"
        if "_parcela_" in sid:
            return f"Parcela média · {fonte}"
        if "_inadimplencia_" in sid:
            return fonte
    if source == "abrainc":
        return f"{name} (Abrainc)"
    if source == "secovi":
        return f"{name} (Secovi-SP)"
    return name.replace(" — ", " · ")


def kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha com os indicadores da página de abertura (último valor e valor de comparação)."""
    def s(src, sid, reg="BR"):
        x = df[(df.source == src) & (df.series_id == sid) & (df.region == reg)].sort_values("date")
        return x.set_index("date")["value"]
    mes = lambda d: ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][int(d[5:7]) - 1] + "/" + d[2:4]
    tri = lambda d: f"{(int(d[5:7]) - 1) // 3 + 1}T{d[2:4]}"
    row = {}
    pf = sum(s("bcb_olinda", f"credito_contratacao_contratado_pf_{k}").fillna(0) for k in FONTE_RECURSO)
    pf = pf.dropna()
    row |= {"credito_12m": pf.iloc[-12:].sum(), "credito_12m_ant": pf.iloc[-24:-12].sum(), "credito_ref": f"até {mes(pf.index[-1])} · BCB"}
    for key, src, sid, lag in [("taxa", "bcb_olinda", "credito_contratacao_taxa_pf_sfh", 12),
                               ("inadimplencia", "bcb_olinda", "credito_estoque_inadimplencia_pf_sfh", 12),
                               ("poupanca", "bcb_olinda", "fontes_sbpe_saldo", 12),
                               ("sinapi", "sidra", "sinapi_custo_m2", 12)]:
        x = s(src, sid).dropna()
        row |= {key: x.iloc[-1], f"{key}_ant": x.iloc[-1 - lag], f"{key}_ref": f"{mes(x.index[-1])} · " + {"bcb_olinda": "BCB", "sidra": "IBGE"}[src]}
    for key, sid in [("lancamentos", "lancamentos"), ("vendas", "vendas")]:
        x = s("cbic", sid).dropna()
        row |= {key: x.iloc[-1], f"{key}_ant": x.iloc[-5], f"{key}_ref": f"{tri(x.index[-1])} · CBIC"}
    x = s("abecip", "igmi_r").dropna()
    row |= {"precos_12m": (x.iloc[-1] / x.iloc[-13] - 1) * 100, "precos_ref": f"{mes(x.index[-1])} · Abecip"}
    row["atualizado_em"] = dt.date.today().strftime("%d/%m/%Y")
    return pd.DataFrame([row])


if __name__ == "__main__":
    main()
