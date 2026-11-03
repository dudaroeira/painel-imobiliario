"""Regras de consistência entre lançamentos financeiros (documento do usuário, 02/11/2026).

Regra 1 - Transferência entre contas da mesma empresa: toda saída classificada como "Transferência entre contas"
    deve ter uma entrada na MESMA empresa, no mesmo dia e com o mesmo valor.
Regra 2 - Transferência entre empresas do grupo: toda saída de aporte de capital, mútuo ou repasse "X P/ Y"
    deve aparecer como entrada em OUTRA empresa, no mesmo dia e com o mesmo valor (qualquer transferência ou
    controle financeiro serve de contrapartida, porque o histórico de quem recebe costuma ser genérico).
    Distribuição de lucros fica fora: quando vai para sócio pessoa física não tem contrapartida nas empresas.

Ordem do pareamento (1 para 1, cada entrada fecha uma única saída):
    1. regra 2 (grupo), para que a entrada genérica de quem recebe um aporte não sobre como "entrada sem saída";
    2. regra 1 (mesma empresa);
    3. saídas da regra 1 que sobraram tentam uma entrada em outra empresa: transferência entre empresas com
       histórico genérico. Fecham a regra, mas ficam marcadas como "fechada via outra empresa".
O que sobra, dos dois lados, vai para a aba "Conferencia" da base.
"""
from __future__ import annotations

import pandas as pd

TIPOS_GRUPO = {"Aporte de capital", "Mútuo entre empresas", "Transferência entre empresas"}
TIPO_CONTAS = "Transferência entre contas"


class _Pareador:
    def __init__(self, entradas: pd.DataFrame):
        self.e = entradas[["Empresa", "Data", "abs"]].copy()
        self.e["usado"] = False

    def parear(self, saidas: pd.DataFrame, mesma_empresa: bool) -> pd.Index:
        """Casa cada saída com uma entrada livre (mesmo dia e valor). Devolve os índices das saídas sem par."""
        sem_par = []
        for i, r in saidas.sort_values("Data").iterrows():
            cand = self.e[(~self.e["usado"]) & (self.e["abs"] == r["abs"]) & (self.e["Data"] == r["Data"])]
            cand = cand[cand["Empresa"] == r["Empresa"]] if mesma_empresa else cand[cand["Empresa"] != r["Empresa"]]
            if len(cand):
                self.e.loc[cand.index[0], "usado"] = True
            else:
                sem_par.append(i)
        return pd.Index(sem_par)

    @property
    def livres(self) -> pd.Index:
        return self.e.index[~self.e["usado"]]


def conferir(movimento: pd.DataFrame, desde: str = "2018-01-01") -> tuple[pd.DataFrame, list[tuple[str, object]]]:
    """Aplica as duas regras à aba Movimento. Devolve (detalhe dos lançamentos sem par, indicadores para o Resumo)."""
    cols = ["Empresa", "Nome empresa", "Data", "Banco", "Conta", "Origem", "Tipo de movimento", "Histórico", "Documento"]
    mv = movimento[movimento["Data"] >= pd.Timestamp(desde)].copy()
    mv["abs"] = (mv["Entrada"] - mv["Saída"]).abs().round(2)
    mv = mv[mv["abs"] > 0]
    transf = mv[mv["Origem"].astype(str).str.upper().str.startswith("TRANSF") | (mv["Origem"] == "CONTROLE FINANCEIRO")]
    entradas = transf[transf["Entrada"] > 0]
    par = _Pareador(entradas)

    s2 = transf[transf["Tipo de movimento"].isin(TIPOS_GRUPO) & (transf["Saída"] > 0)]
    ss2 = par.parear(s2, mesma_empresa=False)
    s1 = transf[(transf["Tipo de movimento"] == TIPO_CONTAS) & (transf["Saída"] > 0)]
    ss1 = par.parear(s1, mesma_empresa=True)
    ss1_outra = ss1.difference(par.parear(transf.loc[ss1], mesma_empresa=False))  # fechadas via outra empresa
    ss1 = ss1.difference(ss1_outra)
    livres = par.livres
    se1 = livres[transf.loc[livres, "Tipo de movimento"] == TIPO_CONTAS]
    se2 = livres[transf.loc[livres, "Tipo de movimento"].isin(TIPOS_GRUPO)]

    def bloco(idx, regra, sentido):
        d = transf.loc[idx, cols + ["abs"]].rename(columns={"abs": "Valor"})
        d.insert(0, "Regra", regra)
        d.insert(1, "Sentido", sentido)
        return d

    r1, r2 = "1 - Transferência entre contas", "2 - Transferência entre empresas"
    detalhe = pd.concat([
        bloco(ss1, r1, "Saída sem entrada"),
        bloco(ss1_outra, r1, "Fechada via outra empresa (histórico genérico)"),
        bloco(se1, r1, "Entrada sem saída"),
        bloco(ss2, r2, "Saída sem entrada em outra empresa"),
        bloco(se2, r2, "Entrada sem saída em outra empresa"),
    ], ignore_index=True).sort_values(["Regra", "Sentido", "Data", "Empresa"]).reset_index(drop=True)

    def pct(parte, todo):
        return f"{(1 - parte / todo) * 100:.1f}%" if todo else "-"

    indicadores = [
        (f"Regra 1: transferências entre contas desde {desde[:4]} (saídas)", len(s1)),
        ("  Saídas sem entrada no mesmo dia e valor (R$)", float(transf.loc[ss1, "abs"].sum())),
        ("  Saídas fechadas (%)", pct(len(ss1), len(s1))),
        ("  Das fechadas, via outra empresa com histórico genérico", len(ss1_outra)),
        (f"Regra 2: aportes, mútuos e repasses entre empresas desde {desde[:4]} (saídas)", len(s2)),
        ("  Saídas sem entrada em outra empresa (R$)", float(transf.loc[ss2, "abs"].sum())),
        ("  Saídas fechadas (%)", pct(len(ss2), len(s2))),
    ]
    return detalhe, indicadores
