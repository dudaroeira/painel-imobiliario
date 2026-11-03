"""Atualização semanal: monta a base única e gera o painel.

    python -m financeiro.atualizar               # pasta mais recente em dados/uau/brutos/
    python -m financeiro.atualizar 2026-11-07    # pasta específica
"""
import sys

from financeiro import montar_base, painel

if __name__ == "__main__":
    montar_base.main(sys.argv[1:])
    painel.gerar()
