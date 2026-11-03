"""Monta a base financeira única a partir das exportações semanais do ERP UAU.

Uso:
    python -m financeiro.montar_base                 # usa a pasta mais recente em dados/uau/brutos/
    python -m financeiro.montar_base 2026-10-31      # usa dados/uau/brutos/2026-10-31/

Entrada (uma pasta por semana, nomes fixos — ver docs/rotina-atualizacao-uau.md):
    contas_a_pagar.xls   Financeiro > Contas a Pagar, todas as obras, "Processos", Imp. > Arquivo XLS
    contas_pagas.csv     Financeiro > Contas Pagas, todas as obras, "Processos", 01/07/2017 até hoje, Exportar
    bancos_saldos.xls    Conciliação > Resumo, todas as contas, mês corrente, Imp. > Arquivo XLS
    bancos_extrato.xls   Conciliação > Extrato, todas as contas, 01/01/2025 até hoje, Imp. > Arquivo XLS
    fluxo_sintetico.xls  Fluxo de caixa > Sintético, todas as configurações, próximos 90 dias

Saída:
    dados/uau/base/base_financeira_<data>.xlsx  e  dados/uau/base/base_financeira_atual.xlsx

Critérios oficiais aplicados (definidos pela empresa):
    1. Empresas 1 a 45, exceto pessoas físicas 4, 34, 35, 36, 37 e 38.
    2. Movimento a partir de 01/07/2017 (implantação do UAU).
    3. Só processos de pagamento (o filtro "Processos" é marcado na exportação).
    4. Bancos -1 (interno) e 999 (controle) fora; banco 0 (sem conta definida) também fora dos saldos.
    5. Fornecedor COMPANHIA IMOBILIARIA DE BRASILIA TERRACAP (código 2813) fora.
"""
from __future__ import annotations

import csv
import io
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BRUTOS = RAIZ / "dados" / "uau" / "brutos"
SAIDA = RAIZ / "dados" / "uau" / "base"

EMPRESAS_PF = {4, 34, 35, 36, 37, 38}
BANCOS_FORA = {-1, 0, 999}
DATA_CORTE = pd.Timestamp("2017-07-01")
TERRACAP = "TERRACAP"


# ---------------------------------------------------------------- leitura
def ler_grade_html(arq: Path) -> pd.DataFrame:
    """As grades do UAU exportadas como 'Arquivo XLS' são tabelas HTML em cp1252."""
    html = arq.read_text(encoding="cp1252")
    return pd.read_html(io.StringIO(html), header=1, thousands=".", decimal=",")[0]


def ler_contas_pagas(arq: Path) -> pd.DataFrame:
    """O CSV de Contas Pagas tem 2 campos a mais nas linhas do que no cabeçalho,
    inseridos antes de 'Data do processo'. Realinha antes de montar o DataFrame."""
    with arq.open(encoding="cp1252", newline="") as fh:
        leitor = csv.reader(fh, delimiter=";")
        cab = next(leitor)
        linhas = list(leitor)
    i = cab.index("Data do processo")
    nomes = cab[:i] + ["_extra1", "_extra2"] + cab[i:]
    largura = len(nomes)
    linhas = [ln + [""] * (largura - len(ln)) if len(ln) < largura else ln[:largura] for ln in linhas]
    return pd.DataFrame(linhas, columns=nomes)


def num(s: pd.Series) -> pd.Series:
    """Converte texto no formato brasileiro (1.234,56) em número."""
    if s.dtype.kind in "fi":
        return s
    t = s.astype(str).str.strip().str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(t.replace({"": None, "nan": None}), errors="coerce")


def dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")


def codigo(s: pd.Series) -> pd.Series:
    """Primeiro número de campos como '1 - Provisionado'."""
    return pd.to_numeric(s.astype(str).str.extract(r"^\s*(-?\d+)")[0], errors="coerce")


def empresa_valida(emp: pd.Series) -> pd.Series:
    e = pd.to_numeric(emp, errors="coerce")
    return e.between(1, 45) & ~e.isin(EMPRESAS_PF)


# ---------------------------------------------------------------- transformações
class Exclusoes:
    def __init__(self):
        self.linhas = []

    def registrar(self, tabela: str, motivo: str, df: pd.DataFrame, col_valor: str | None):
        if len(df):
            valor = float(df[col_valor].sum()) if col_valor else None
            self.linhas.append({"Tabela": tabela, "Motivo": motivo, "Linhas": len(df), "Valor": valor})

    def df(self):
        return pd.DataFrame(self.linhas, columns=["Tabela", "Motivo", "Linhas", "Valor"])


def filtrar(df: pd.DataFrame, regras, exc: Exclusoes, tabela: str, col_valor: str | None) -> pd.DataFrame:
    """Aplica as regras em sequência, registrando o que cada uma removeu."""
    for motivo, cond in regras:
        mask = cond(df).fillna(False).astype(bool)
        exc.registrar(tabela, motivo, df[mask], col_valor)
        df = df[~mask]
    return df.copy()


def faixa_vencimento(dias: float) -> str:
    if dias < 0:
        return "Vencido"
    if dias <= 30:
        return "A vencer 0-30"
    if dias <= 60:
        return "A vencer 31-60"
    if dias <= 90:
        return "A vencer 61-90"
    return "A vencer 90+"


def aging(dias: float) -> str:
    if dias >= 0:
        return ""
    a = -dias
    for lim, nome in ((30, "1-30 dias"), (60, "31-60 dias"), (90, "61-90 dias"), (180, "91-180 dias"), (365, "181-365 dias")):
        if a <= lim:
            return nome
    return "Mais de 365 dias"


def montar_pagar(raw: pd.DataFrame, hoje: pd.Timestamp, exc: Exclusoes) -> pd.DataFrame:
    b = pd.DataFrame({
        "Empresa": pd.to_numeric(raw["Empresa"], errors="coerce"),
        "Nome empresa": raw["Desc. empresa"],
        "Obra": raw["Obra"].astype(str),
        "Nome obra": raw["Desc. obra"],
        "Fornecedor": raw["Cheque nominal"].astype(str),
        "Processo": raw["Proc."],
        "Parcela": raw["Parcela"],
        "Documento": raw["Doc. fiscal"],
        "Emissão": dt(raw["Dt. doc. fiscal"]),
        "Vencimento original": dt(raw["Vencimento"]),
        "Vencimento": dt(raw["Prorrogação"]),
        "Valor": num(raw["Valor a pagar"]).fillna(0),
        "Categoria": raw.get("Desc. categ. mov. financ."),
        "Tipo de origem": raw["Tipo de origem"],
        "Operação": raw["Operação"],
        "Aprovação": raw["Confirmado"],
        "Status NF": raw["Status NF"],
    })
    b["Vencimento"] = b["Vencimento"].fillna(b["Vencimento original"])
    b = filtrar(b, [
        ("Empresa fora de 1-45 ou pessoa física", lambda d: ~empresa_valida(d["Empresa"])),
        ("Fornecedor TERRACAP", lambda d: d["Fornecedor"].str.upper().str.contains(TERRACAP)),
    ], exc, "A pagar", "Valor")
    b["Dias para vencer"] = (b["Vencimento"] - hoje).dt.days
    b["Situação"] = b["Dias para vencer"].map(lambda d: "Vencido" if d < 0 else "A vencer")
    b["Faixa"] = b["Dias para vencer"].map(faixa_vencimento)
    b["Aging"] = b["Dias para vencer"].map(aging)
    b["Mês vencimento"] = b["Vencimento"].dt.to_period("M").astype(str)
    return b.sort_values(["Empresa", "Obra", "Vencimento"]).reset_index(drop=True)


def montar_pagas(raw: pd.DataFrame, exc: Exclusoes) -> pd.DataFrame:
    b = pd.DataFrame({
        "Empresa": pd.to_numeric(raw["Empresa"], errors="coerce"),
        "Nome empresa": raw["Descr. Empresa"],
        "Obra": raw["Obra"],
        "Nome obra": raw["Descr. Obra"],
        "Fornecedor": raw["Nominal"],
        "Processo": raw["Processo"],
        "Parcela": raw["Parcela"],
        "Documento": raw["Doc. Fiscal"],
        "Emissão documento": dt(raw["Dt. Doc. Fiscal"]),
        "Vencimento": dt(raw["Dt. Vencimento"]),
        "Pagamento": dt(raw["Dt. pagamento"]),
        "Valor pago": num(raw["Valor Pago"]).fillna(0),
        "Valor parcela": num(raw["Valor Parcela"]),
        "Acréscimos": num(raw["Acréscimos"]),
        "Descontos": num(raw["Descontos"]),
        "CAP": raw["CAP"],
        "Descrição CAP": raw["Descrição do CAP"],
        "Categoria": raw["Desc. Categ. Mov. Fin."],
        "Banco": pd.to_numeric(raw["Banco"], errors="coerce"),
        "Conta": raw["Conta"],
        "Tipo emissão": raw["Tipo Emissão"],
        "Tipo de origem": pd.to_numeric(raw["Tipo de Origem"], errors="coerce"),
        "Grupo de obra": raw["Descrição grupo de obra"],
    })
    b["Pagamento"] = b["Pagamento"].fillna(b["Vencimento"])
    regras = [
        ("Empresa fora de 1-45 ou pessoa física", lambda d: ~empresa_valida(d["Empresa"])),
        ("Pagamento antes de 01/07/2017", lambda d: d["Pagamento"] < DATA_CORTE),
        ("Banco -1 ou 999", lambda d: d["Banco"].isin({-1, 999})),
        ("Fornecedor TERRACAP", lambda d: d["Fornecedor"].astype(str).str.upper().str.contains(TERRACAP)),
    ]
    b = filtrar(b, regras, exc, "Pagas", "Valor pago")
    b = b.copy()
    b["Mês pagamento"] = b["Pagamento"].dt.to_period("M").astype(str)
    b["Ano"] = b["Pagamento"].dt.year
    return b.sort_values(["Pagamento", "Empresa", "Obra"]).reset_index(drop=True)


def montar_saldos(raw: pd.DataFrame, exc: Exclusoes) -> pd.DataFrame:
    b = pd.DataFrame({
        "Empresa": pd.to_numeric(raw["Empresa"], errors="coerce"),
        "Nome empresa": raw["Descrição empresa"],
        "Banco": pd.to_numeric(raw["Banco"], errors="coerce"),
        "Nome banco": raw["Descrição"],
        "Conta": raw["Conta"].astype(str),
        "Descrição conta": raw["Descrição.1"],
        "Tipo conta": raw["Tipo conta"],
        "Saldo anterior": num(raw["Saldo anterior"]).fillna(0),
        "Entradas no mês": num(raw["Entradas no período"]).fillna(0),
        "Saídas no mês": num(raw["Saídas no período"]).fillna(0),
        "Saldo atual": num(raw["Saldo atual"]).fillna(0),
    })
    b = filtrar(b, [
        ("Empresa fora de 1-45 ou pessoa física", lambda d: ~empresa_valida(d["Empresa"])),
        ("Banco -1, 0 ou 999", lambda d: d["Banco"].isin(BANCOS_FORA)),
        ("Conta do tipo Controle", lambda d: d["Tipo conta"].astype(str).str.startswith("4")),
    ], exc, "Saldos", "Saldo atual")
    return b.sort_values(["Empresa", "Banco", "Conta"]).reset_index(drop=True)


def montar_extrato(raw: pd.DataFrame, exc: Exclusoes) -> pd.DataFrame:
    tipo = raw["Tipo Lanc."].astype(str)
    valor = num(raw["Valor"]).fillna(0)
    entrada = tipo.str.startswith("1 -")
    b = pd.DataFrame({
        "Empresa": pd.to_numeric(raw["Empresa"], errors="coerce"),
        "Nome empresa": raw["Descrição empresa"],
        "Banco": pd.to_numeric(raw["Banco"], errors="coerce"),
        "Nome banco": raw["Descrição"],
        "Conta": raw["Conta"].astype(str),
        "Descrição conta": raw["Descrição.1"],
        "Data": dt(raw["Data"]),
        "Documento": raw["No. Doc."],
        "Histórico": raw["Histórico"],
        "Tipo lançamento": tipo,
        "Entrada": valor.where(entrada, 0.0),
        "Saída": valor.where(~entrada, 0.0),
    })
    b["Valor líquido"] = b["Entrada"] - b["Saída"]
    b = filtrar(b, [
        ("Empresa fora de 1-45 ou pessoa física", lambda d: ~empresa_valida(d["Empresa"])),
        ("Banco -1, 0 ou 999", lambda d: d["Banco"].isin(BANCOS_FORA)),
    ], exc, "Extrato", "Saída")
    b = b.copy()
    b["Mês"] = b["Data"].dt.to_period("M").astype(str)
    return b.sort_values(["Data", "Empresa", "Banco", "Conta"]).reset_index(drop=True)


FIRMES = ["Pagar incorrido", "Pagar comprometido", "Pagar contratado", "Tributo", "Saída controle financ.",
          "Distrato", "Comissão", "Contas unid.", "Repasse alug.", "Securitização", "Requisição de compra"]
RECEBER = ["A receber consolidado", "Recebida a depositar", "Contrato de venda", "Entrada controle financ."]


def montar_fluxo(sint: pd.DataFrame, saldos: pd.DataFrame, exc: Exclusoes) -> pd.DataFrame:
    """Resumo do fluxo de caixa do UAU (próximos 90 dias) por empresa, separado por natureza.

    O 'Saldo inicial fluxo' do UAU soma lançamentos de extrato nunca conciliados (em algumas
    contas, bilhões acumulados) e por isso NÃO é usado: o saldo de partida é o saldo real da
    aba Saldos. A 'Saída planejada' é orçamento (planejamento de obra), não título lançado,
    e fica numa coluna própria, fora do saldo projetado.
    """
    s = sint.copy()
    s["Empresa"] = pd.to_numeric(s["Empresa"], errors="coerce")
    s["Banco"] = pd.to_numeric(s["Banco"], errors="coerce")
    s = filtrar(s, [
        ("Empresa fora de 1-45 ou pessoa física", lambda d: ~empresa_valida(d["Empresa"])),
        ("Banco -1 ou 999", lambda d: d["Banco"].isin({-1, 999})),
    ], exc, "Fluxo projetado", None)
    for c in s.columns[5:]:
        s[c] = num(s[c]).fillna(0)
    s["Não conciliado no UAU"] = s["Lançamentos de entrada"] - s["Lançamentos de saída"]
    g = s.groupby("Empresa").agg(**{
        "Nome empresa": ("Descrição da empresa", "first"),
        "Saída planejada": ("Saída planejada", "sum"),
        "Entrada planejada": ("Entrada planejada", "sum"),
        "Não conciliado no UAU": ("Não conciliado no UAU", "sum"),
    })
    g["Despesas firmes (UAU)"] = s.groupby("Empresa")[[c for c in FIRMES if c in s]].sum().sum(axis=1)
    g["A receber"] = s.groupby("Empresa")[[c for c in RECEBER if c in s]].sum().sum(axis=1)
    g["Saldo atual"] = saldos.groupby("Empresa")["Saldo atual"].sum().reindex(g.index).fillna(0)
    g["Saldo após firmes e a receber"] = g["Saldo atual"] - g["Despesas firmes (UAU)"] + g["A receber"]
    cols = ["Nome empresa", "Saldo atual", "Despesas firmes (UAU)", "A receber", "Saldo após firmes e a receber",
            "Saída planejada", "Entrada planejada", "Não conciliado no UAU"]
    return g[cols].reset_index()


def projetar_saldo(pagar: pd.DataFrame, saldos: pd.DataFrame, hoje: pd.Timestamp, dias: int = 90) -> pd.DataFrame:
    """Saldo diário por empresa = saldo real hoje − contas a pagar acumuladas até cada dia.
    Parcelas vencidas entram no primeiro dia. Recebimentos não entram (o UAU só dá o total)."""
    datas = pd.date_range(hoje, hoje + pd.Timedelta(days=dias), freq="D")
    p = pagar.assign(Dia=pagar["Vencimento"].clip(lower=hoje).dt.normalize())
    emps = sorted(set(saldos["Empresa"]) | set(p["Empresa"]))
    nomes = pd.concat([saldos[["Empresa", "Nome empresa"]], p[["Empresa", "Nome empresa"]]]).drop_duplicates("Empresa").set_index("Empresa")["Nome empresa"]
    saldo0 = saldos.groupby("Empresa")["Saldo atual"].sum()
    por_dia = p.groupby(["Empresa", "Dia"])["Valor"].sum()
    linhas = []
    for e in emps:
        serie = por_dia.get(e, pd.Series(dtype=float)).reindex(datas, fill_value=0.0).cumsum()
        for d, acum in serie.items():
            linhas.append((d, e, nomes.get(e, ""), float(saldo0.get(e, 0.0)), float(acum), float(saldo0.get(e, 0.0) - acum)))
    return pd.DataFrame(linhas, columns=["Data", "Empresa", "Nome empresa", "Saldo atual", "A pagar acumulado", "Saldo projetado"])


# ---------------------------------------------------------------- saída
def resumo(pagar, pagas, saldos, extrato, hoje) -> pd.DataFrame:
    ult12 = pagas[pagas["Pagamento"] > hoje - pd.DateOffset(months=12)]
    linhas = [
        ("Data de referência", hoje.strftime("%d/%m/%Y")),
        ("Contas a pagar em aberto (R$)", pagar["Valor"].sum()),
        ("  Vencido (R$)", pagar.loc[pagar["Situação"] == "Vencido", "Valor"].sum()),
        ("  A vencer em 30 dias (R$)", pagar.loc[pagar["Faixa"] == "A vencer 0-30", "Valor"].sum()),
        ("Parcelas em aberto", len(pagar)),
        ("Saldo bancário em contas reais (R$)", saldos["Saldo atual"].sum()),
        ("Pago nos últimos 12 meses (R$)", ult12["Valor pago"].sum()),
        ("Pagamentos na base (linhas)", len(pagas)),
        ("Primeiro pagamento na base", pagas["Pagamento"].min().strftime("%d/%m/%Y")),
        ("Lançamentos de extrato na base", len(extrato)),
    ]
    return pd.DataFrame(linhas, columns=["Indicador", "Valor"])


def salvar(abas: dict[str, pd.DataFrame], destino: Path):
    pd.to_pickle(abas, destino.with_suffix(".pkl"))
    with pd.ExcelWriter(destino, engine="xlsxwriter", datetime_format="dd/mm/yyyy", date_format="dd/mm/yyyy",
                        engine_kwargs={"options": {"constant_memory": True}}) as w:
        moeda = w.book.add_format({"num_format": "#,##0.00"})
        for nome, df in abas.items():
            df.to_excel(w, sheet_name=nome, index=False)
            ws = w.sheets[nome]
            ws.freeze_panes(1, 0)
            if len(df):
                ws.autofilter(0, 0, len(df), len(df.columns) - 1)
            # constant_memory grava linha a linha; larguras e formatos são definidos antes dos dados pelo pandas,
            # então aqui só ajustamos colunas (não afeta as células já escritas no modo streaming)
            for i, col in enumerate(df.columns):
                amostra = [len(str(v)) for v in df[col].head(200)] or [0]
                larg = min(max(len(str(col)), *amostra) + 2, 45)
                ws.set_column(i, i, larg, moeda if df[col].dtype.kind == "f" else None)


def projetar_caixa(pagar: pd.DataFrame, receber: pd.DataFrame, saldos: pd.DataFrame, hoje: pd.Timestamp, dias: int = 90) -> pd.DataFrame:
    """Saldo diário por empresa = saldo real hoje − a pagar acumulado (vencidos no 1º dia)
    e, na 2ª série, + a receber acumulado só das parcelas ainda a vencer (as vencidas são
    inadimplência e ficam fora). Traz as séries separadas para o painel."""
    datas = pd.date_range(hoje, hoje + pd.Timedelta(days=dias), freq="D")
    p = pagar.assign(Dia=pagar["Vencimento"].clip(lower=hoje).dt.normalize())
    r = receber[receber["Vencimento"] >= hoje].assign(Dia=receber.loc[receber["Vencimento"] >= hoje, "Vencimento"].dt.normalize())
    emps = sorted(set(saldos["Empresa"]) | set(p["Empresa"]) | set(r["Empresa"]))
    nomes = pd.concat([saldos[["Empresa", "Nome empresa"]], p[["Empresa", "Nome empresa"]], r[["Empresa", "Nome empresa"]]]) \
        .drop_duplicates("Empresa").set_index("Empresa")["Nome empresa"]
    saldo0 = saldos.groupby("Empresa")["Saldo atual"].sum()
    pd_dia = p.groupby(["Empresa", "Dia"])["Valor"].sum()
    rd_dia = r.groupby(["Empresa", "Dia"])["Valor"].sum()
    linhas = []
    for e in emps:
        ap = pd_dia.get(e, pd.Series(dtype=float)).reindex(datas, fill_value=0.0).cumsum()
        ar = rd_dia.get(e, pd.Series(dtype=float)).reindex(datas, fill_value=0.0).cumsum()
        s0 = float(saldo0.get(e, 0.0))
        for d in datas:
            linhas.append((d, e, nomes.get(e, ""), s0, float(ap[d]), float(ar[d]), s0 - float(ap[d]), s0 - float(ap[d]) + float(ar[d])))
    return pd.DataFrame(linhas, columns=["Data", "Empresa", "Nome empresa", "Saldo atual", "A pagar acumulado",
                                         "A receber acumulado", "Saldo só com pagamentos", "Saldo com recebimentos"])


def classificar_prazo(df: pd.DataFrame, hoje: pd.Timestamp) -> pd.DataFrame:
    df = df.copy()
    df["Dias para vencer"] = (df["Vencimento"] - hoje).dt.days
    df["Situação"] = df["Dias para vencer"].map(lambda d: "Vencido" if d < 0 else "A vencer")
    df["Faixa"] = df["Dias para vencer"].map(faixa_vencimento)
    df["Aging"] = df["Dias para vencer"].map(aging)
    df["Mês vencimento"] = df["Vencimento"].dt.to_period("M").astype(str)
    return df


def resumo13(pagar, receber, pagas, recebidas, saldos, hoje, anos_m1) -> pd.DataFrame:
    ult12 = pagas[pagas["Pagamento"] > hoje - pd.DateOffset(months=12)]
    rec12 = recebidas[recebidas["Recebimento"] > hoje - pd.DateOffset(months=12)] if len(recebidas) else recebidas
    linhas = [
        ("Data de referência", hoje.strftime("%d/%m/%Y")),
        ("Contas a pagar em aberto (R$)", pagar["Valor"].sum()),
        ("  Vencido (R$)", pagar.loc[pagar["Situação"] == "Vencido", "Valor"].sum()),
        ("  A vencer em 30 dias (R$)", pagar.loc[pagar["Faixa"] == "A vencer 0-30", "Valor"].sum()),
        ("Contas a receber em aberto (R$)", receber["Valor"].sum()),
        ("  Vencido (R$)", receber.loc[receber["Situação"] == "Vencido", "Valor"].sum()),
        ("  A vencer em 30 dias (R$)", receber.loc[receber["Faixa"] == "A vencer 0-30", "Valor"].sum()),
        ("Saldo bancário em contas reais (R$)", saldos["Saldo atual"].sum()),
        ("Pago nos últimos 12 meses (R$)", ult12["Valor pago"].sum()),
        ("Recebido nos últimos 12 meses (R$)", rec12["Valor recebido"].sum() if len(rec12) else 0.0),
        ("Pagamentos na base (linhas)", len(pagas)),
        ("Primeiro pagamento na base", pagas["Pagamento"].min().strftime("%d/%m/%Y")),
        ("Anos com recebidos/movimento (estrutura 13 modo 1)", ", ".join(str(a) for a in anos_m1)),
    ]
    return pd.DataFrame(linhas, columns=["Indicador", "Valor"])


def main(argv: list[str]) -> None:
    from financeiro import estrutura13 as e13
    if argv:
        pasta = BRUTOS / argv[0]
    else:
        pasta = sorted(p for p in BRUTOS.iterdir() if p.is_dir())[-1]
    hoje = pd.Timestamp(datetime.strptime(pasta.name, "%Y-%m-%d").date())
    print(f"Pasta de entrada: {pasta}")
    exc = Exclusoes()
    saldos = montar_saldos(ler_grade_html(pasta / "bancos_saldos.xls"), exc)

    if (pasta / "base13_modo0_apagar_areceber.xls").exists():
        # ---- fonte principal: estrutura 13 do Visualizador ----
        from financeiro import historico
        import glob as _glob
        m0 = e13._ler(pasta / "base13_modo0_apagar_areceber.xls")
        for f in sorted(_glob.glob(str(historico.PASTA / "base13_modo1_*.xls"))) + sorted(_glob.glob(str(pasta / "base13_modo1_*.xls"))):
            rem, add = historico.incorporar(Path(f))
            if add:
                print(f"  histórico: {Path(f).name}: -{rem} +{add} linhas")
        m1 = historico.carregar()
        anos_m1 = historico.anos_cobertos()
        pagar = e13.a_pagar(m0)
        pagar = filtrar(pagar, [("Fornecedor TERRACAP", lambda d: d["Fornecedor"].astype(str).str.upper().str.contains(TERRACAP))],
                        exc, "A pagar", "Valor")
        pagar = classificar_prazo(pagar, hoje).sort_values(["Empresa", "Obra", "Vencimento"]).reset_index(drop=True)
        receber = classificar_prazo(e13.a_receber(m0), hoje).sort_values(["Empresa", "Obra", "Vencimento"]).reset_index(drop=True)

        pagas = e13.pagas(m1) if len(m1) else pd.DataFrame()
        if len(pagas):
            pagas = filtrar(pagas, [
                ("Pagamento antes de 01/07/2017", lambda d: d["Pagamento"] < DATA_CORTE),
                ("Banco -1 ou 999", lambda d: d["Banco"].isin({-1, 999})),
                ("Fornecedor TERRACAP", lambda d: d["Fornecedor"].astype(str).str.upper().str.contains(TERRACAP)),
            ], exc, "Pagas", "Valor pago")
            pagas["Fonte"] = "Estrutura 13"
        # ponte: anos sem arquivo modo 1 vêm do CSV de Contas Pagas, se existir
        csv = pasta / "contas_pagas.csv"
        if not csv.exists():
            csv = RAIZ / "dados" / "uau" / "historico" / "contas_pagas.csv"
        if csv.exists():
            cache = csv.with_suffix(".pkl")
            if cache.exists() and cache.stat().st_mtime >= csv.stat().st_mtime:
                antigas = pd.read_pickle(cache)
            else:
                antigas = montar_pagas(ler_contas_pagas(csv), exc)
                antigas.to_pickle(cache)
            antigas = antigas[~antigas["Pagamento"].dt.year.isin(anos_m1)].copy()
            antigas["Fonte"] = "Contas Pagas (CSV)"
            if len(pagas):
                comuns = [c for c in pagas.columns if c in antigas.columns]
                pagas = pd.concat([pagas[comuns], antigas[comuns]], ignore_index=True)
            else:
                pagas = antigas
        pagas["Mês pagamento"] = pagas["Pagamento"].dt.to_period("M").astype(str)
        pagas["Ano"] = pagas["Pagamento"].dt.year
        pagas = pagas.sort_values(["Pagamento", "Empresa", "Obra"]).reset_index(drop=True)

        recebidas = e13.recebidas(m1) if len(m1) else pd.DataFrame(columns=["Empresa", "Recebimento", "Valor recebido"])
        if len(recebidas):
            recebidas["Mês recebimento"] = recebidas["Recebimento"].dt.to_period("M").astype(str)
        movimento = e13.movimento(m1) if len(m1) else pd.DataFrame()
        if len(movimento):
            movimento = filtrar(movimento, [("Banco -1, 0 ou 999", lambda d: d["Banco"].isin(BANCOS_FORA))], exc, "Movimento", "Saída")
            movimento["Mês"] = movimento["Data"].dt.to_period("M").astype(str)
        saldo_proj = projetar_caixa(pagar, receber, saldos, hoje)
        fluxo = montar_fluxo(ler_grade_html(pasta / "fluxo_sintetico.xls"), saldos, exc) if (pasta / "fluxo_sintetico.xls").exists() else pd.DataFrame()
        fonte = "estrutura 13 (consulta 29) do Visualizador + Conciliação > Resumo"
        from financeiro import consistencia
        conferencia, ind_conf = consistencia.conferir(movimento) if len(movimento) else (pd.DataFrame(), [])
        resumo_df = resumo13(pagar, receber, pagas, recebidas, saldos, hoje, anos_m1)
        resumo_df = pd.concat([resumo_df, pd.DataFrame(ind_conf, columns=["Indicador", "Valor"])], ignore_index=True)
        abas = {
            "Resumo": resumo_df,
            "A pagar": pagar, "A receber": receber, "Pagas": pagas, "Recebidas": recebidas,
            "Saldos": saldos, "Movimento": movimento, "Saldo projetado diario": saldo_proj,
            "Fluxo projetado": fluxo, "Conferencia": conferencia,
        }
    else:
        # ---- fonte antiga: grades do Financeiro ----
        pagar = montar_pagar(ler_grade_html(pasta / "contas_a_pagar.xls"), hoje, exc)
        pagas = montar_pagas(ler_contas_pagas(pasta / "contas_pagas.csv"), exc)
        extrato = montar_extrato(ler_grade_html(pasta / "bancos_extrato.xls"), exc)
        fluxo = montar_fluxo(ler_grade_html(pasta / "fluxo_sintetico.xls"), saldos, exc)
        saldo_proj = projetar_saldo(pagar, saldos, hoje)
        fonte = "grades Contas a Pagar, Contas Pagas, Conciliação e Fluxo de caixa"
        abas = {
            "Resumo": resumo(pagar, pagas, saldos, extrato, hoje),
            "A pagar": pagar, "Pagas": pagas, "Saldos": saldos, "Extrato": extrato,
            "Fluxo projetado": fluxo, "Saldo projetado diario": saldo_proj,
        }

    abas["Exclusoes"] = exc.df()
    abas["Criterios"] = pd.DataFrame({"Critério": [
        "Empresas 1 a 45, exceto pessoas físicas 4, 34, 35, 36, 37 e 38",
        "Movimento a partir de 01/07/2017 (implantação do UAU)",
        "Somente processos de pagamento (sem transações financeiras)",
        "Bancos -1 (interno) e 999 (controle) desconsiderados; banco 0 e contas do tipo Controle fora dos saldos",
        "Saldo projetado = saldo real de hoje − a pagar acumulado por vencimento (série 'com recebimentos' soma o a receber); vencidos no 1º dia",
        "O saldo inicial do fluxo de caixa do UAU inclui lançamentos de extrato não conciliados e não é usado",
        "Fornecedor COMPANHIA IMOBILIARIA DE BRASILIA TERRACAP (2813) desconsiderado",
        f"Fonte: {fonte}, exportações de {pasta.name}, montadas por financeiro/montar_base.py",
    ]})
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / f"base_financeira_{pasta.name}.xlsx"
    salvar(abas, destino)
    shutil.copyfile(destino, SAIDA / "base_financeira_atual.xlsx")
    shutil.copyfile(destino.with_suffix(".pkl"), SAIDA / "base_financeira_atual.pkl")
    for nome, df in abas.items():
        print(f"  {nome:<24} {len(df):>8} linhas")
    print(f"Base gravada em {destino}")


if __name__ == "__main__":
    main(sys.argv[1:])
