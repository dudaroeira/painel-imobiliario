"""Monta o SQL completo da consulta 29 a partir do modelo do repositório e da lista de contas (fora do git).

    python -m financeiro.montar_sql

Lê financeiro/sql_base_painel.sql (modelo, com o marcador <<LISTA_CONTAS>>) e dados/uau/contas_consulta29.txt
(uma conta por linha, no formato banco|conta, ex.: 999|12345-6) e grava dados/uau/sql_base_painel_completo.sql,
que é o texto a colar na consulta 29 do UAU. A lista de contas não vai para o repositório porque ele é público.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "financeiro" / "sql_base_painel.sql"
CONTAS = RAIZ / "dados" / "uau" / "contas_consulta29.txt"
SAIDA = RAIZ / "dados" / "uau" / "sql_base_painel_completo.sql"
MARCADOR = "<<LISTA_CONTAS>>"


def montar() -> Path:
    contas = [c.strip() for c in CONTAS.read_text(encoding="utf-8").splitlines() if c.strip()]
    if not contas:
        raise SystemExit(f"Lista de contas vazia: {CONTAS}")
    modelo = MODELO.read_text(encoding="utf-8")
    if modelo.count(MARCADOR) != 3:
        raise SystemExit(f"Esperava 3 marcadores {MARCADOR} no modelo, achei {modelo.count(MARCADOR)}")
    SAIDA.write_text(modelo.replace(MARCADOR, ",".join(contas)), encoding="utf-8")
    return SAIDA


if __name__ == "__main__":
    print(f"{len(CONTAS.read_text(encoding='utf-8').split())} contas -> {montar()}")
