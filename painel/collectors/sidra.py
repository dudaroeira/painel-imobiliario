"""IBGE — API SIDRA: SINAPI (custo da construção) e PIB da construção (Contas Nacionais Trimestrais).

API: https://apisidra.ibge.gov.br/values/t/{tabela}/n{nivel}/all/v/{variavel}/p/all[/c{class}/{cat}]
"""
from __future__ import annotations

from .. import http, store

API = "https://apisidra.ibge.gov.br/values/" + "{path}"

QUERIES = [
    # SINAPI custo médio m² — Brasil e UFs
    dict(path="t/2296/n1/all/v/1198/p/all", sid="sinapi_custo_m2_var12m", name="SINAPI — custo médio m² (var. 12 meses)",
         block="custos", unit="%", freq="M"),
    # variável 48 = custo médio m² em moeda corrente (R$); 1196 é a variação mensal
    dict(path="t/2296/n1/all/v/48/p/all", sid="sinapi_custo_m2", name="SINAPI — custo médio m²",
         block="custos", unit="R$/m²", freq="M"),
    dict(path="t/2296/n3/all/v/48/p/all", sid="sinapi_custo_m2", name="SINAPI — custo médio m²",
         block="custos", unit="R$/m²", freq="M"),
    # PIB construção — índice de volume dessazonalizado e variação a/a
    dict(path="t/1621/n1/all/v/584/p/all/c11255/90691", sid="pib_construcao_indice", name="PIB construção — índice de volume (dessaz.)",
         block="custos", unit="índice (1995=100)", freq="Q"),
    dict(path="t/5932/n1/all/v/6561/p/all/c11255/90691", sid="pib_construcao_var_aa", name="PIB construção — var. contra mesmo trim. ano anterior",
         block="custos", unit="%", freq="Q"),
    dict(path="t/5932/n1/all/v/6561/p/all/c11255/90707", sid="pib_total_var_aa", name="PIB total — var. contra mesmo trim. ano anterior",
         block="macro", unit="%", freq="Q"),
]

UF_SIGLA = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
            "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
            "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF", "1": "BR"}


def _period_to_date(code: str, freq: str) -> str:
    if freq == "M":  # 202607
        return f"{code[:4]}-{code[4:6]}-01"
    if freq == "Q":  # 202601 = 1º trimestre
        q = int(code[4:6])
        return f"{code[:4]}-{(q - 1) * 3 + 1:02d}-01"
    return f"{code[:4]}-01-01"


def collect(refresh: bool = True):
    out = []
    for q in QUERIES:
        try:
            data = http.get_json(API.format(path=q["path"]), cache_name=f"sidra/{q['sid']}_{q['path'].split('/')[3]}.json", refresh=refresh)
        except Exception as e:
            print(f"[sidra] {q['sid']} falhou: {e}")
            continue
        for r in data[1:]:  # linha 0 é o cabeçalho
            if r["V"] in ("...", "-", "X", "..", None):
                continue
            # D1 = território, D3 = período (mês/trimestre). Identifica a coluna de período pelo nome.
            per_key = next((k for k in r if k.endswith("C") and r[k.replace("C", "N")] in ("Mês", "Trimestre")), None)
            # fallback: no SIDRA o período é sempre D3C para estas tabelas
            pcode = r[per_key] if per_key else r["D3C"]
            out.append(dict(source="sidra", series_id=q["sid"], name=q["name"], block=q["block"],
                            region=UF_SIGLA.get(r["D1C"], r["D1N"]), unit=q["unit"], freq=q["freq"],
                            date=_period_to_date(pcode, q["freq"]), value=r["V"]))
    df = store.frame(out)
    store.save(df, "sidra", {"url": "https://apisidra.ibge.gov.br", "title": "IBGE — SIDRA (SINAPI, PIB construção)",
                             "coverage": "Brasil e UFs"})
    return df


if __name__ == "__main__":
    collect()
