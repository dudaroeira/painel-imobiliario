"""Data de fechamento de caixa (conciliação) por empresa, a partir do UAU.

Tela: Financeiro > Fechamento de Caixa/Conta. Empresa = "Vários" (todas), período de 01/01 do ano anterior até
hoje (pelo calendário ao lado do período; os campos de data não aceitam digitação), Fechamento Fiscal, Diário
(Caixa) e Banco/Conta marcados > Buscar > clicar numa linha > Imp. > Arquivo XLS > `fechamentos_caixa.xls` na
pasta da semana. É só consulta: não clicar em "Fechamento" na barra da tela.

O caixa é fechado cerca de 15 dias depois do fim do mês, quando as contas estão conciliadas. Até essa data os
valores do painel são definitivos; depois dela podem mudar.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

EMPRESAS_PF = {4, 34, 35, 36, 37, 38}


def ler(arq: Path) -> dict:
    """Devolve {"geral": "dd/mm/aaaa", "porEmpresa": {"1": "dd/mm/aaaa", ...}} só para empresas 1-45 sem PF."""
    if not arq.exists():
        return {}
    t = pd.read_html(io.StringIO(arq.read_text(encoding="cp1252")), header=1)[0]
    t["Data"] = pd.to_datetime(t["Data"], format="%d/%m/%Y", errors="coerce")
    t["Empresa"] = pd.to_numeric(t["Empresa"], errors="coerce")
    t = t[t["Status"].astype(str).str.startswith("1") & t["Fechamento"].astype(str).str.contains("Caixa")]
    t = t[t["Empresa"].between(1, 45) & ~t["Empresa"].isin(EMPRESAS_PF)]
    t = t[~t.iloc[:, t.columns.str.startswith("Descri").argmax()].astype(str).str.upper().str.contains("TESTE")]
    if t.empty:
        return {}
    ult = t.groupby("Empresa")["Data"].max()
    return {
        "geral": ult.min().strftime("%d/%m/%Y"),
        "porEmpresa": {str(int(e)): d.strftime("%d/%m/%Y") for e, d in ult.items()},
    }


def da_semana(raiz: Path) -> dict:
    """Lê o fechamentos_caixa.xls mais recente das pastas da semana."""
    brutos = raiz / "dados" / "uau" / "brutos"
    for pasta in sorted((p for p in brutos.iterdir() if p.is_dir()), reverse=True):
        if (pasta / "fechamentos_caixa.xls").exists():
            return ler(pasta / "fechamentos_caixa.xls")
    return {}
