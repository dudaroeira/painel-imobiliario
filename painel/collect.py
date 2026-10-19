"""Roda todos os coletores e grava data/series/*.csv + data/catalog.csv.

Uso:  python -m painel.collect            (todas as fontes)
      python -m painel.collect secovi abecip   (só as indicadas)
      python -m painel.collect --no-refresh    (usa o cache em data/raw)
"""
from __future__ import annotations

import sys
import traceback

from . import store
from .collectors import abecip, abrainc, bcb_olinda, bcb_sgs, fipezap, secovi, sidra

COLLECTORS = {
    "bcb_olinda": bcb_olinda.collect,
    "bcb_sgs": bcb_sgs.collect,
    "sidra": sidra.collect,
    "fipezap": fipezap.collect,
    "abecip": abecip.collect,
    "abrainc": abrainc.collect,
    "secovi": secovi.collect,
}


def main(argv: list[str]):
    refresh = "--no-refresh" not in argv
    names = [a for a in argv if not a.startswith("--")] or list(COLLECTORS)
    failed = []
    for n in names:
        print(f"\n=== {n} ===")
        try:
            COLLECTORS[n](refresh=refresh)
        except Exception:
            traceback.print_exc()
            failed.append(n)
    cat = store.catalog()
    cat.to_csv(store.DATA / "catalog.csv", index=False, encoding="utf-8")
    print(f"\nCatálogo: {len(cat)} séries em {cat['source'].nunique()} fontes → data/catalog.csv")
    if failed:
        print("FALHARAM:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
