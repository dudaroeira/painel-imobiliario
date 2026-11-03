"""Gera o painel financeiro interativo (HTML autossuficiente) a partir da base única.

Uso:
    python -m financeiro.painel                       # lê dados/uau/base/base_financeira_atual.xlsx
    python -m financeiro.painel caminho/da/base.xlsx

Saída: dados/uau/painel/painel_financeiro.html (abre direto no navegador, sem servidor).
O arquivo contém dados internos do ERP: fica em dados/, que está fora do Git.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BASE_PADRAO = RAIZ / "dados" / "uau" / "base" / "base_financeira_atual.xlsx"
SAIDA = RAIZ / "dados" / "uau" / "painel" / "painel_financeiro.html"
TEMPLATE = Path(__file__).with_name("painel_template.html")


def r2(x) -> float:
    return round(float(x), 2)


class Dic:
    """Dicionário de textos repetidos (fornecedores, obras) para encolher o JSON."""

    def __init__(self):
        self.idx: dict[str, int] = {}
        self.lista: list[str] = []

    def __call__(self, s) -> int:
        s = "" if pd.isna(s) else str(s).strip()
        if s not in self.idx:
            self.idx[s] = len(self.lista)
            self.lista.append(s)
        return self.idx[s]


def carregar(base: Path) -> dict:
    pkl = base.with_suffix(".pkl")
    if pkl.exists() and pkl.stat().st_mtime >= base.stat().st_mtime - 60:
        abas_pkl = pd.read_pickle(pkl)
        def ler(aba, usecols=None, **kw):
            df = abas_pkl[aba]
            return df[[c for c in usecols if c in df.columns]].copy() if usecols else df.copy()
    else:
        ler = lambda aba, **kw: pd.read_excel(base, sheet_name=aba, **kw)
    resumo = ler("Resumo")
    pagar = ler("A pagar")
    cols_pagas = ler("Pagas").columns
    cap_col = "Descrição CAP" if "Descrição CAP" in cols_pagas else "Categoria"
    pagas = ler("Pagas", usecols=["Empresa", "Nome empresa", "Obra", "Nome obra", "Fornecedor",
                                   "Pagamento", "Valor pago", cap_col])
    pagas = pagas.rename(columns={cap_col: "Descrição CAP"})
    saldos = ler("Saldos")
    abas = list(abas_pkl.keys()) if pkl.exists() else pd.ExcelFile(base).sheet_names
    extrato = ler("Movimento" if "Movimento" in abas else "Extrato",
                  usecols=["Empresa", "Nome empresa", "Data", "Entrada", "Saída", "Tipo de movimento"])
    proj = ler("Saldo projetado diario")
    fluxo = ler("Fluxo projetado")
    receber = ler("A receber") if "A receber" in abas else pd.DataFrame(columns=["Empresa", "Nome empresa", "Obra", "Nome obra", "Cliente", "Vencimento", "Valor", "Produto", "Venda-Parcela"])
    recebidas = ler("Recebidas", usecols=["Empresa", "Obra", "Recebimento", "Valor recebido"]) if "Recebidas" in abas else pd.DataFrame(columns=["Empresa", "Obra", "Recebimento", "Valor recebido"])

    data_ref = str(resumo.loc[resumo["Indicador"] == "Data de referência", "Valor"].iloc[0])
    forn, txt = Dic(), Dic()

    # dimensões
    empresas: dict[int, str] = {}
    obras: dict[str, dict] = {}
    for df, ce in ((pagar, "Nome empresa"), (pagas, "Nome empresa"), (saldos, "Nome empresa"),
                   (extrato, "Nome empresa"), (proj, "Nome empresa"), (receber, "Nome empresa")):
        for e, n in df[["Empresa", ce]].drop_duplicates().itertuples(index=False):
            if pd.notna(e):
                empresas.setdefault(int(e), str(n).strip())
    for df in (pagar, pagas, receber):
        for e, o, n in df[["Empresa", "Obra", "Nome obra"]].drop_duplicates().itertuples(index=False):
            obras.setdefault(f"{int(e)}|{o}", {"e": int(e), "o": str(o), "n": str(n).strip()})

    # contas a receber: detalhe e recebidas por mês
    receber_rows = [
        [int(r.Empresa), str(r.Obra), txt(r.Cliente), r.Vencimento.strftime("%Y-%m-%d"), r2(r.Valor),
         txt(r.Produto), str(r._7) if pd.notna(r._7) else ""]
        for r in receber[["Empresa", "Obra", "Cliente", "Vencimento", "Valor", "Produto", "Nome obra", "Venda-Parcela"]].itertuples(index=False)
    ] if len(receber) else []
    if len(recebidas):
        recebidas["mes"] = recebidas["Recebimento"].dt.strftime("%Y-%m")
        rm = recebidas.groupby(["mes", "Empresa", "Obra"], as_index=False)["Valor recebido"].sum()
        recebidas_mes = [[m, int(e), str(o), r2(v)] for m, e, o, v in rm.itertuples(index=False)]
    else:
        recebidas_mes = []

    # contas a pagar: detalhe
    pagar_rows = [
        [int(r.Empresa), str(r.Obra), forn(r.Fornecedor), r.Vencimento.strftime("%Y-%m-%d"),
         r2(r.Valor), str(r.Documento) if pd.notna(r.Documento) else "", str(r.Processo)]
        for r in pagar.itertuples(index=False)
    ]

    # pagas: mês x empresa x obra; ano x empresa x obra x fornecedor; ano x empresa x obra x CAP
    pagas["mes"] = pagas["Pagamento"].dt.strftime("%Y-%m")
    pagas["ano"] = pagas["Pagamento"].dt.year
    pm = pagas.groupby(["mes", "Empresa", "Obra"], as_index=False)["Valor pago"].sum()
    pagas_mes = [[m, int(e), str(o), r2(v)] for m, e, o, v in pm.itertuples(index=False)]
    pf = pagas.groupby(["ano", "Empresa", "Obra", "Fornecedor"], as_index=False)["Valor pago"].agg(["sum", "size"])
    pagas_forn = [[int(a), int(e), str(o), forn(f), r2(v), int(n)] for a, e, o, f, v, n in pf.itertuples(index=False)]
    pagas["Descrição CAP"] = pagas["Descrição CAP"].fillna("Sem CAP")
    pc = pagas.groupby(["ano", "Empresa", "Obra", "Descrição CAP"], as_index=False)["Valor pago"].sum()
    pagas_cap = [[int(a), int(e), str(o), txt(c), r2(v)] for a, e, o, c, v in pc.itertuples(index=False)]

    # caixa
    saldos_rows = [
        [int(e), str(b).strip(), str(c), str(d).strip(), str(t), r2(v)]
        for e, b, c, d, t, v in saldos[["Empresa", "Nome banco", "Conta", "Descrição conta",
                                        "Tipo conta", "Saldo atual"]].itertuples(index=False)
    ]
    extrato["mes"] = extrato["Data"].dt.strftime("%Y-%m")
    em = extrato.groupby(["mes", "Empresa"], as_index=False)[["Entrada", "Saída"]].sum()
    extrato_mes = [[m, int(e), r2(a), r2(b)] for m, e, a, b in em.itertuples(index=False)]
    # movimento por tipo: ano x empresa x tipo -> entradas, saídas, nº de lançamentos
    if "Tipo de movimento" in extrato.columns:
        extrato["ano"] = extrato["Data"].dt.year
        mt = extrato.groupby(["ano", "Empresa", "Tipo de movimento"], as_index=False).agg(
            Entrada=("Entrada", "sum"), Saída=("Saída", "sum"), n=("Entrada", "size"))
        mov_tipo = [[int(a), int(e), txt(t), r2(x), r2(y), int(n)] for a, e, t, x, y, n in mt.itertuples(index=False)]
    else:
        mov_tipo = []
    if "Saldo com recebimentos" in proj.columns:
        pj = proj.groupby(["Data", "Empresa"], as_index=False)[["Saldo só com pagamentos", "Saldo com recebimentos"]].sum()
        proj_rows = [[d.strftime("%Y-%m-%d"), int(e), r2(a), r2(b)] for d, e, a, b in pj.itertuples(index=False)]
    else:
        pj = proj.groupby(["Data", "Empresa"], as_index=False)["Saldo projetado"].sum()
        proj_rows = [[d.strftime("%Y-%m-%d"), int(e), r2(v), None] for d, e, v in pj.itertuples(index=False)]
    fluxo_rows = [[int(r["Empresa"]), r2(r["Saldo atual"]), r2(r["Despesas firmes (UAU)"]), r2(r["A receber"]),
                   r2(r["Saldo após firmes e a receber"]), r2(r["Saída planejada"]), r2(r["Não conciliado no UAU"])]
                  for _, r in fluxo.iterrows()]

    return {
        "dataRef": data_ref,
        "empresas": {str(k): v for k, v in sorted(empresas.items())},
        "obras": list(obras.values()),
        "fornecedores": forn.lista,
        "textos": txt.lista,
        "pagar": pagar_rows,
        "pagasMes": pagas_mes,
        "pagasForn": pagas_forn,
        "pagasCap": pagas_cap,
        "saldos": saldos_rows,
        "extratoMes": extrato_mes,
        "movTipo": mov_tipo,
        "projecao": proj_rows,
        "fluxo": fluxo_rows,
        "receber": receber_rows,
        "recebidasMes": recebidas_mes,
    }


def gerar(base: Path = BASE_PADRAO, destino: Path = SAIDA) -> Path:
    dados = carregar(base)
    payload = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DADOS__*/null", payload)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    print(f"Painel gravado em {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
    return destino


if __name__ == "__main__":
    gerar(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_PADRAO)
