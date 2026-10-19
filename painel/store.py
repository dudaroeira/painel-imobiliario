"""Camada de dados: tabela longa (uma linha por observação) + catálogo de séries.

Colunas da tabela longa:
    source     fonte (bcb_olinda, bcb_sgs, sidra, fipezap, abecip, abrainc, secovi)
    series_id  identificador estável dentro da fonte
    name       nome legível
    block      bloco do painel (oferta, credito, funding, precos, custos, macro, imoveis)
    region     'BR', sigla de UF ou nome de cidade
    unit       unidade (R$ mi, unidades, %, índice ...)
    freq       'M' mensal, 'Q' trimestral, 'D' diário
    date       primeiro dia do período (YYYY-MM-DD)
    value      float
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
SERIES_DIR = DATA / "series"
for p in (RAW, SERIES_DIR):
    p.mkdir(parents=True, exist_ok=True)

COLUMNS = ["source", "series_id", "name", "block", "region", "unit", "freq", "date", "value"]


def frame(rows: list[dict]) -> pd.DataFrame:
    """Normaliza uma lista de dicionários para o esquema longo."""
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).drop_duplicates(["source", "series_id", "region", "date"], keep="last")
    return df.sort_values(["source", "series_id", "region", "date"]).reset_index(drop=True)


def save(df: pd.DataFrame, source: str, meta: dict) -> Path:
    """Grava data/series/<source>.csv e o metadado da coleta."""
    out = SERIES_DIR / f"{source}.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    meta = {
        **meta,
        "source": source,
        "collected_at": dt.datetime.now().isoformat(timespec="seconds"),
        "rows": int(len(df)),
        "series": int(df["series_id"].nunique()),
        "first_date": df["date"].min() if len(df) else None,
        "last_date": df["date"].max() if len(df) else None,
    }
    (SERIES_DIR / f"{source}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{source}] {meta['rows']:>8} linhas | {meta['series']:>5} séries | {meta['first_date']} → {meta['last_date']}")
    return out


def load_all() -> pd.DataFrame:
    parts = [pd.read_csv(p, dtype={"region": str}) for p in sorted(SERIES_DIR.glob("*.csv"))]
    if not parts:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(parts, ignore_index=True)


def load_meta() -> dict:
    return {p.stem.replace(".meta", ""): json.loads(p.read_text(encoding="utf-8")) for p in SERIES_DIR.glob("*.meta.json")}


def catalog(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Uma linha por (source, series_id): nome, bloco, unidade, regiões, período."""
    df = load_all() if df is None else df
    g = df.groupby(["source", "series_id", "name", "block", "unit", "freq"], as_index=False).agg(
        regions=("region", lambda s: ",".join(sorted(set(s)))),
        n_regions=("region", "nunique"),
        first_date=("date", "min"),
        last_date=("date", "max"),
        n=("value", "size"),
    )
    return g.sort_values(["block", "source", "series_id"]).reset_index(drop=True)
