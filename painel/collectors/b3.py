"""B3 — estoque registrado de LCI, LIG, CRI e LCA (Boletim Diário do Mercado, tabela "Estoque").

Substitui as séries fontes_lci/lig/cri do BCB, encerradas em fev/2025. O boletim diário é um PDF
em várias partes (BDI_01 … BDI_07) em arquivos.b3.com.br; a tabela de estoque muda de parte
conforme a edição, por isso o coletor procura em todas até achar os três instrumentos.
Série mensal = último dia útil de cada mês, desde abr/2023 (quando a tabela passou a existir).
"""
from __future__ import annotations

import calendar
import datetime as dt
import io
import re

import pdfplumber
import requests

from .. import http, store

URL = "https://arquivos.b3.com.br/bdi/download/bdi/{d}/BDI_{part:02d}_{dd}.pdf"
INSTR = {"LCI": ("b3_estoque_lci", "Estoque de LCI registrado na B3"),
         "LIG": ("b3_estoque_lig", "Estoque de LIG registrado na B3"),
         "CRI": ("b3_estoque_cri", "Estoque de CRI registrado na B3"),
         "LCA": ("b3_estoque_lca", "Estoque de LCA registrado na B3")}
ROW_RE = re.compile(r"^(LCI|LIG|CRI|LCA)\s+((?:[\d.]+|-)\s+){4}")
FIRST = (2023, 4)


def _fetch(url: str, cache: str) -> bytes | None:
    path = http.RAW / cache
    if path.exists():
        return path.read_bytes()
    try:
        r = requests.get(url, headers={"User-Agent": http.UA}, timeout=180)
    except requests.RequestException:
        return None
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.content


def parse(pdf: bytes) -> dict[str, float]:
    """Linhas 'LCI <qtd emitida> <qtd mercado> <qtd depositada> <volume mercado> <volume depositado>' -> {instr: volume em mercado (R$)}."""
    out = {}
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for pg in doc.pages:
            text = pg.extract_text() or ""
            if "stoque" not in text:
                continue
            for ln in text.splitlines():
                m = ROW_RE.match(ln)
                if not m or m.group(1) in out:
                    continue
                nums = ln.split()[1:]
                if len(nums) >= 5 and nums[3] != "-":
                    out[m.group(1)] = float(nums[3].replace(".", ""))
            if len(out) == len(INSTR):
                break
    return out


def month_end_values(y: int, m: int) -> tuple[str, dict] | None:
    """Procura o último dia do mês com boletim e devolve (data, valores)."""
    last = calendar.monthrange(y, m)[1]
    for day in range(last, last - 8, -1):
        d = dt.date(y, m, day)
        if d.weekday() >= 5 or d >= dt.date.today():
            continue
        found = {}
        # ordem por probabilidade: a partir de dez/2025 a tabela está na parte 01; antes, na parte 04
        # (renda fixa). A parte 02 (ações) tem dezenas de MB e fica por último.
        for part in (1, 4, 5, 7, 6, 3, 2):
            pdf = _fetch(URL.format(d=d.isoformat(), part=part, dd=d.strftime("%Y%m%d")), f"b3/BDI_{part:02d}_{d:%Y%m%d}.pdf")
            if pdf is None:
                if part == 1:
                    break  # não há boletim nesse dia
                continue
            found.update({k: v for k, v in parse(pdf).items() if k not in found})
            if len(found) == len(INSTR):
                break
        if found:
            return d.isoformat(), found
    return None


def collect(refresh: bool = True):
    prev = store.SERIES_DIR / "b3.csv"
    rows = []
    done = set()
    if prev.exists():
        import pandas as pd
        old = pd.read_csv(prev)
        rows = old.to_dict("records")
        done = set(old["date"].str[:7])
        if done:  # o mês mais recente é refeito (pode ter sido coletado antes do fim do mês)
            done.discard(max(done))
            rows = [r for r in rows if r["date"][:7] != max(old["date"].str[:7])]
    today = dt.date.today()
    y, m = FIRST
    while (y, m) <= (today.year, today.month):
        key = f"{y}-{m:02d}"
        if key not in done:
            res = month_end_values(y, m)
            if res:
                _, vals = res
                for instr, (sid, name) in INSTR.items():
                    if instr in vals:
                        rows.append(dict(source="b3", series_id=sid, name=name, block="funding", region="BR", unit="R$", freq="M",
                                         date=f"{y}-{m:02d}-01", value=vals[instr]))
                print(f"[b3] {key}: " + ", ".join(f"{k} {v/1e9:,.1f} bi" for k, v in vals.items()))
            else:
                print(f"[b3] {key}: boletim não encontrado")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    df = store.frame(rows)
    store.save(df, "b3", {"url": "https://arquivos.b3.com.br/bdi/", "title": "B3 — Boletim Diário do Mercado (estoque registrado)",
                          "coverage": "Brasil; volume em mercado dos instrumentos registrados na B3, último dia útil de cada mês"})
    return df


if __name__ == "__main__":
    collect()
