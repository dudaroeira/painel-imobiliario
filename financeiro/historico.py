"""Histórico acumulado do modo 1 da estrutura 13 (pagos, recebidos, transferências, controles).

Cada exportação do modo 1 cobre um período [Inicio, Fim] (colunas do próprio arquivo). Ao incorporar
um arquivo, as linhas do histórico dentro desse período são substituídas pelas novas: assim a carga
semanal pode cobrir os últimos 15 dias com segurança, e uma reexportação de um ano inteiro corrige o ano.

Arquivos:
    dados/uau/historico/movimento_e13.pkl         histórico tratado (DataFrame, nível de item)
    dados/uau/historico/movimento_e13_cargas.json  cargas já incorporadas (nome, tamanho, período)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from financeiro import estrutura13 as e13

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "dados" / "uau" / "historico"
ARQ = PASTA / "movimento_e13.pkl"
MANIFEST = PASTA / "movimento_e13_cargas.json"


def carregar() -> pd.DataFrame:
    return pd.read_pickle(ARQ) if ARQ.exists() else pd.DataFrame()


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def ja_incorporado(arq: Path) -> bool:
    m = _manifest().get(arq.name)
    return bool(m) and m.get("tamanho") == arq.stat().st_size


def incorporar(arq: Path, forcar: bool = False) -> tuple[int, int]:
    """Lê um XLS do modo 1 e o incorpora ao histórico. Devolve (linhas removidas, linhas adicionadas)."""
    if ja_incorporado(arq) and not forcar:
        return (0, 0)
    novo = e13._ler(arq)
    ini, fim = novo["Inicio"].min(), novo["Fim"].max()
    hist = carregar()
    removidas = 0
    if len(hist):
        dentro = hist["Emissao"].between(ini, fim)
        removidas = int(dentro.sum())
        hist = hist[~dentro]
    hist = pd.concat([hist, novo], ignore_index=True) if len(hist) else novo
    hist = hist.sort_values(["Emissao", "Empresa", "Obra"]).reset_index(drop=True)
    PASTA.mkdir(parents=True, exist_ok=True)
    hist.to_pickle(ARQ)
    m = _manifest()
    m[arq.name] = {"tamanho": arq.stat().st_size, "inicio": str(ini.date()), "fim": str(fim.date()),
                   "linhas": int(len(novo)), "incorporado_em": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    return (removidas, int(len(novo)))


def periodos_cobertos() -> list[tuple[str, str]]:
    return sorted((v["inicio"], v["fim"]) for v in _manifest().values())


def anos_cobertos() -> list[int]:
    """Anos que têm pelo menos um pagamento no histórico da estrutura 13."""
    h = carregar()
    if not len(h):
        return []
    return sorted(int(a) for a in h.loc[h["Origem"] == "CONTAS PAGAS", "Emissao"].dt.year.dropna().unique())
