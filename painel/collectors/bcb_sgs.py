"""BCB — Sistema Gerenciador de Séries Temporais (SGS), séries macro.

API: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=dd/mm/aaaa
"""
from __future__ import annotations

import datetime as dt

from .. import http, store

BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

# code: (series_id, nome, bloco, unidade, freq)
SERIES = {
    432: ("selic_meta", "Selic — meta definida pelo Copom", "macro", "% a.a.", "D"),
    4390: ("selic_mensal", "Selic acumulada no mês", "macro", "% a.m.", "M"),
    433: ("ipca", "IPCA — variação mensal", "macro", "% a.m.", "M"),
    13522: ("ipca_12m", "IPCA — acumulado 12 meses", "macro", "%", "M"),
    192: ("incc_di", "INCC-DI (FGV) — variação mensal", "custos", "% a.m.", "M"),
    189: ("igpm", "IGP-M — variação mensal", "macro", "% a.m.", "M"),
    226: ("tr", "TR — taxa referencial", "macro", "% a.m.", "D"),
    1835: ("poupanca_saldo_total", "Depósitos de poupança — saldo total", "funding", "R$ mil", "M"),
    24364: ("ibc_br", "IBC-Br (dessazonalizado)", "macro", "índice", "M"),
    24369: ("desemprego", "Taxa de desocupação (PNAD Contínua)", "macro", "%", "M"),
}


def _parse_date(s: str) -> str:
    d = dt.datetime.strptime(s, "%d/%m/%Y")
    return d.strftime("%Y-%m-%d")


def collect(start="01/01/2008", refresh: bool = True):
    out, ok = [], []
    # séries diárias: a API exige dataFinal e janela de até ~8 anos (senão devolve HTML "Requisição inválida"),
    # por isso o histórico desde `start` é baixado em janelas menores
    today = dt.date.today()
    windows = []
    w0 = dt.datetime.strptime(start, "%d/%m/%Y").date()
    while w0 < today:
        w1 = min(today, w0.replace(year=w0.year + 5) - dt.timedelta(days=1))  # janelas de 5 anos: algumas de 8 são recusadas
        windows.append((w0, w1))
        w0 = w1 + dt.timedelta(days=1)
    for code, (sid, name, block, unit, freq) in SERIES.items():
        try:
            if freq == "D":
                data = []
                for i, (a, b) in enumerate(windows):
                    data += http.get_json(BASE.format(code=code), params={"formato": "json", "dataInicial": a.strftime("%d/%m/%Y"), "dataFinal": b.strftime("%d/%m/%Y")},
                                          cache_name=f"bcb_sgs/{code}_{i}.json", refresh=refresh)
            else:
                data = http.get_json(BASE.format(code=code), params={"formato": "json", "dataInicial": start}, cache_name=f"bcb_sgs/{code}.json", refresh=refresh)
        except Exception as e:  # API instável: mantém o que já havia sido coletado para essa série
            print(f"[bcb_sgs] código {code} ({sid}) falhou: {e} — mantendo dados anteriores")
            prev = store.SERIES_DIR / "bcb_sgs.csv"
            if prev.exists():
                import pandas as pd
                old = pd.read_csv(prev)
                out += old[old.series_id == sid].to_dict("records")
            continue
        ok.append(code)
        for r in data:
            d = _parse_date(r["data"])
            if freq == "M":
                d = d[:8] + "01"
            out.append(dict(source="bcb_sgs", series_id=sid, name=name, block=block, region="BR",
                            unit=unit, freq=freq, date=d, value=r["valor"]))
    df = store.frame(out)
    # Versões mensais das séries diárias: Selic = último valor do mês; TR = valor do dia 1 (TR do mês)
    extra = []
    for sid, how, new_sid, new_name in [("selic_meta", "last", "selic_meta_m", "Selic — meta (fim do mês)"),
                                        ("tr", "first", "tr_m", "TR — taxa referencial (mensal)")]:
        s = df[df.series_id == sid].copy()
        if len(s):
            s["date"] = s["date"].str[:8] + "01"
            s = s.drop_duplicates(["date"], keep=how).assign(series_id=new_sid, freq="M", name=new_name)
            extra += s.to_dict("records")
    if extra:
        df = store.frame(df.to_dict("records") + extra)
    store.save(df, "bcb_sgs", {"url": "https://api.bcb.gov.br/dados/serie/", "title": "BCB — SGS (macro)",
                               "codes": ok, "coverage": "Brasil"})
    return df


if __name__ == "__main__":
    collect()
