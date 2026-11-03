"""Leitura da estrutura 13 "Base painel financeiro" do UAU (Visualizador de resultados).

Arquivos esperados na pasta da semana (dados/uau/brutos/AAAA-MM-DD/):
    base13_modo0_apagar_areceber.xls   relatório 0, período 01/07/2017 a 31/12/2035
    base13_modo1_*.xls                 relatório 1 (pagos + recebidos + transferências + controles), últimos ~15 dias
O modo 1 é acumulado por financeiro/historico.py (substituição por período [Inicio, Fim]); a carga inicial
ano a ano (2017–2025) vai em dados/uau/historico/base13_modo1_<ano>.xls.

Cada arquivo é a grade "Registros" exportada por Imp. > Arquivo XLS (tabela HTML, cp1252), 37 colunas,
uma linha por ITEM do processo. As funções abaixo agregam por parcela (Empresa + Chave1; Chave1 = fornecedor_processo_parcela,
que se repete entre empresas porque o número do processo reinicia por empresa).
"""
from __future__ import annotations

import glob
import io
import re
from pathlib import Path

import pandas as pd

TERRACAP = "TERRACAP"
EMPRESAS_PF = {4, 34, 35, 36, 37, 38}
BANCOS_FORA = {-1, 0, 999}


def _ler(arq: Path) -> pd.DataFrame:
    html = arq.read_text(encoding="cp1252")
    df = pd.read_html(io.StringIO(html), header=1, thousands=".", decimal=",")[0]
    df["Empresa"] = pd.to_numeric(df["Empresa"], errors="coerce")
    df["Banco"] = pd.to_numeric(df["Banco"], errors="coerce")
    for c in ("Vencimento", "Emissao", "DtNF", "Inicio", "Fim"):
        df[c] = pd.to_datetime(df[c], format="%d/%m/%Y", errors="coerce")
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)
    df["Obra"] = df["Obra"].astype(str)
    df["_arquivo"] = arq.name
    return df


def carregar(pasta: Path, historico: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list[int]]:
    """Devolve (modo0, modo1, anos cobertos pelo modo 1)."""
    m0 = _ler(pasta / "base13_modo0_apagar_areceber.xls")
    arquivos: dict[int, Path] = {}
    for base in ([historico] if historico and historico.exists() else []) + [pasta]:
        for f in sorted(glob.glob(str(base / "base13_modo1_*.xls"))):
            m = re.search(r"modo1_(\d{4})", f)
            if m:
                arquivos[int(m.group(1))] = Path(f)  # a pasta da semana sobrescreve o histórico
    m1 = pd.concat([_ler(f) for f in arquivos.values()], ignore_index=True) if arquivos else pd.DataFrame()
    return m0, m1, sorted(arquivos)


def _nome_empresa(df: pd.DataFrame) -> pd.Series:
    return df["DescEmpresa"].astype(str).str.replace(r"^\d+\s*-\s*", "", regex=True).str.strip()


def _nome_obra(df: pd.DataFrame) -> pd.Series:
    return df["DescObra"].astype(str).str.replace(r"^\S+\s*-\s*", "", regex=True).str.strip()


def _moda(s: pd.Series):
    s = s.dropna()
    return s.mode().iloc[0] if len(s) else None


def a_pagar(m0: pd.DataFrame) -> pd.DataFrame:
    """Parcelas a pagar (uma linha por parcela, valor = soma dos itens)."""
    d = m0[m0["Origem"] == "CONTAS A PAGAR"].copy()
    d["Valor"] = -d["Valor"]
    d["Nome empresa"] = _nome_empresa(d)
    d["Nome obra"] = _nome_obra(d)
    g = d.groupby(["Empresa", "Chave1"], sort=False).agg(
        Empresa=("Empresa", "first"), **{"Nome empresa": ("Nome empresa", "first")},
        Obra=("Obra", "first"), **{"Nome obra": ("Nome obra", "first")},
        Fornecedor=("Fornecedor", "first"), CNPJ=("CNPJ", "first"),
        Processo=("Processo", "first"), Documento=("NF", "first"),
        **{"Emissão": ("DtNF", "first"), "Vencimento original": ("Vencimento", "first"),
           "Vencimento": ("Emissao", "first")},
        Valor=("Valor", "sum"), Categoria=("Descr_Comp", _moda), Produto=("Produto", "first"),
        Itens=("Item", "size"),
    ).reset_index(drop=True)
    g["Parcela"] = d.groupby(["Empresa", "Chave1"], sort=False)["Chave1"].first().str.split("_").str[-1].values
    g["Vencimento"] = g["Vencimento"].fillna(g["Vencimento original"])
    return g


def a_receber(m0: pd.DataFrame) -> pd.DataFrame:
    d = m0[m0["Origem"] == "CONTAS RECEBER"].copy()
    out = pd.DataFrame({
        "Empresa": d["Empresa"], "Nome empresa": _nome_empresa(d),
        "Obra": d["Obra"], "Nome obra": _nome_obra(d),
        "Cliente": d["Nominal"], "CPF/CNPJ": d["CNPJ"],
        "Venda-Parcela": d["Processo"], "Tipo parcela": d["TipoParc"],
        "Produto": d["Descr_Comp"],
        "Vencimento original": d["Vencimento"], "Vencimento": d["Emissao"].fillna(d["Vencimento"]),
        "Valor": d["Valor"],
    })
    return out.reset_index(drop=True)


def pagas(m1: pd.DataFrame) -> pd.DataFrame:
    d = m1[m1["Origem"] == "CONTAS PAGAS"].copy()
    d["Valor"] = -d["Valor"]
    d["Nome empresa"] = _nome_empresa(d)
    d["Nome obra"] = _nome_obra(d)
    g = d.groupby(["Empresa", "Chave1"], sort=False).agg(
        Empresa=("Empresa", "first"), **{"Nome empresa": ("Nome empresa", "first")},
        Obra=("Obra", "first"), **{"Nome obra": ("Nome obra", "first")},
        Fornecedor=("Fornecedor", "first"), CNPJ=("CNPJ", "first"),
        Processo=("Processo", "first"), Documento=("NF", "first"),
        **{"Emissão documento": ("DtNF", "first"), "Vencimento": ("Vencimento", "first"),
           "Pagamento": ("Emissao", "first"), "Valor pago": ("Valor", "sum")},
        Categoria=("Descr_Comp", _moda), Produto=("Produto", "first"),
        Banco=("Banco", "first"), Conta=("Conta", "first"), Itens=("Item", "size"),
    ).reset_index(drop=True)
    g["Parcela"] = d.groupby(["Empresa", "Chave1"], sort=False)["Chave1"].first().str.split("_").str[-1].values
    return g


def recebidas(m1: pd.DataFrame) -> pd.DataFrame:
    d = m1[m1["Origem"] == "RECEBIDAS"].copy()
    return pd.DataFrame({
        "Empresa": d["Empresa"], "Nome empresa": _nome_empresa(d),
        "Obra": d["Obra"], "Nome obra": _nome_obra(d),
        "Cliente": d["Nominal"], "CPF/CNPJ": d["CNPJ"],
        "Venda-Parcela": d["Processo"], "Tipo parcela": d["TipoParc"], "Produto": d["Descr_Comp"],
        "Vencimento": d["Vencimento"], "Recebimento": d["Emissao"], "Valor recebido": d["Valor"],
        "Banco": d["Banco"], "Conta": d["Conta"],
    }).reset_index(drop=True)


# Tipo de movimento das transferências e controles financeiros, deduzido do histórico do lançamento
# (HistLanc no UAU). A primeira regra que casar vence; a ordem importa (ex.: "devolução de aporte" é aporte,
# "rendimento de aplicação" é rendimento, não aplicação). Texto sem acentos e em maiúsculas.
_REGRAS_TIPO: list[tuple[str, str]] = [
    (r"APORTE", "Aporte de capital"),
    (r"MUTUO", "Mútuo entre empresas"),
    (r"DISTRI", "Distribuição de lucros"),
    (r"RENDIMENTO|REMUNERACAO DE APLIC", "Rendimento de aplicação"),
    (r"TARIFA|CUSTAS|CESTA|IOF|DEB\.? ?SICOOB|DEBITO SICOOB|TX\.? ?BANC|MANUTENCAO DE CONTA|ANUIDADE|TED|DOC\b|PIX\b.*TARIFA",
     "Tarifa bancária"),
    (r"APLICA|RESGATE|INVESTIMENTO|LCI|CDB|FUNDO|PREVIDENCIA|POUPANCA", "Aplicação financeira"),
    (r"EMPRESTIMO|FINANCIAMENTO|AMORTIZA|CEDULA|CCB|BNDES|PLANO EMPRESARIO|CONGA|CAPITAL DE GIRO|JUROS DE FIN|PARCELA DE FIN",
     "Empréstimo bancário"),
    (r"CAUCAO|CAU\b", "Caução e garantias"),
    (r"TAXA DE ADM|TX DE ADM|TX\.? ADM|TITULO DE ADM|TAXA ADM", "Taxa de administração"),
    (r"ESTORNO|DEVOLU|INDEVIDO|CHEQUE DEVOLVIDO", "Estorno e devolução"),
    (r"IRRF|IMPOSTO|DARF|INSS|FGTS|ISS\b|TRIBUTO|GPS\b|IPTU", "Impostos e encargos"),
    (r"JUROS", "Juros e encargos"),
    (r"COMISSAO|RECEITA|REPASSE|VENDA|DESPESAS? RECUPERAD|RESSARCIMENTO|RESTITUI|REESTITUI", "Receitas diversas"),
    (r"\bP/ ", "Transferência entre empresas"),  # "APEX P/ AX", "INCORP 07 P/ APEX": repasse entre empresas do grupo
    (r"TRANSF", "Transferência entre contas"),
]


def _sem_acento(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.upper().str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii"))


def classificar_movimento(origem: pd.Series, historico: pd.Series) -> pd.Series:
    """Tipo de movimento por linha. Pagos e recebidos têm tipo fixo; transferências e controles seguem _REGRAS_TIPO."""
    txt = _sem_acento(historico).str.replace(r"^\d{3}\s+", "", regex=True).str.strip()
    tipo = pd.Series("Outros controles", index=historico.index, dtype=object)
    for padrao, nome in reversed(_REGRAS_TIPO):  # aplica de trás para frente: a primeira regra prevalece
        tipo = tipo.mask(txt.str.contains(padrao, regex=True, na=False), nome)
    orig = _sem_acento(origem)
    tipo = tipo.mask(orig.str.startswith("TRANSFER") & (tipo == "Outros controles"), "Transferência entre contas")
    tipo = tipo.mask(orig == "CONTAS PAGAS", "Pagamento a fornecedor")
    tipo = tipo.mask(orig == "RECEBIDAS", "Recebimento de cliente")
    return tipo


def movimento(m1: pd.DataFrame) -> pd.DataFrame:
    """Todo o movimento bancário do modo 1 (pagos, recebidos, transferências, controles), uma linha por item."""
    d = m1.copy()
    return pd.DataFrame({
        "Empresa": d["Empresa"], "Nome empresa": _nome_empresa(d),
        "Obra": d["Obra"], "Banco": d["Banco"], "Conta": d["Conta"],
        "Data": d["Emissao"], "Origem": d["Origem"], "Histórico": d["Nominal"],
        "Tipo de movimento": classificar_movimento(d["Origem"], d["Nominal"]),
        "Documento": d["NF"], "Entrada": d["Valor"].clip(lower=0), "Saída": (-d["Valor"]).clip(lower=0),
    }).reset_index(drop=True)
