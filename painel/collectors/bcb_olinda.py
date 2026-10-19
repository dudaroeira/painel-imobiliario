"""BCB — Informações do Mercado Imobiliário (API Olinda, OData).

Um único recurso com colunas Data/Info/Valor; ~1.950 séries mensais desde 2014, quase todas
com recorte por UF (sufixo _br, _sp, ...). Documentação:
https://www.bcb.gov.br/estatisticas/mercadoimobiliario
"""
from __future__ import annotations

import re

from .. import http, store

BASE = "https://olinda.bcb.gov.br/olinda/servico/MercadoImobiliario/versao/v1/odata/mercadoimobiliario"
PAGE = 100_000

UFS = "ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to br".split()
_UF_RE = re.compile(r"_(" + "|".join(UFS) + r")$")

FONTE = {"sfh": "SFH/SBPE", "fgts": "FGTS", "livre": "Taxa de mercado (SFI)", "home_equity": "Home equity", "comercial": "Imóvel comercial"}
INDEX = {"tr": "TR", "ipca": "IPCA", "prefixado": "Prefixado", "cdi": "CDI", "outros": "Outros"}
PESSOA = {"pf": "PF", "pj": "PJ"}

# família -> (bloco, unidade, nome base). Famílias fora do dicionário são ignoradas.
FAMILIES = {
    "credito_contratacao_contratado": ("credito", "R$", "Crédito contratado"),
    "credito_contratacao_taxa": ("credito", "% a.a.", "Taxa média das contratações"),
    "credito_contratacao_ltv": ("credito", "%", "LTV médio das contratações"),
    "credito_contratacao_indexador": ("credito", "R$", "Contratações por indexador"),
    "credito_estoque_carteira_credito": ("credito", "R$", "Saldo da carteira"),
    "credito_estoque_inadimplencia": ("credito", "%", "Inadimplência da carteira"),
    "credito_estoque_ativo_problematico": ("credito", "%", "Ativos problemáticos"),
    "credito_estoque_indexador": ("credito", "R$", "Carteira por indexador"),
    "credito_estoque_parcela": ("credito", "R$", "Parcela média"),
    "fontes": ("funding", "R$", "Funding"),
    "direcionamento": ("funding", "R$", "Direcionamento da poupança"),
    "imoveis": ("imoveis", "", "Imóveis financiados"),
    "indices": ("macro", "índice", "Índices"),
}


def _describe(info: str):
    m = _UF_RE.search(info)
    region = m.group(1).upper() if m else "BR"
    base = _UF_RE.sub("", info)
    for fam, (block, unit, label) in FAMILIES.items():
        if base.startswith(fam):
            rest = base[len(fam):].strip("_").split("_")
            parts = []
            if fam.startswith("credito"):
                pessoa = PESSOA.get(rest[0], rest[0]) if rest else ""
                key = "_".join(rest[1:])
                sub = FONTE.get(key) or INDEX.get(key) or key
                parts = [label, pessoa, sub]
            elif fam == "fontes":
                sub = {"sbpe_saldo": "Saldo da poupança SBPE", "lci": "Estoque de LCI", "lig": "Estoque de LIG", "cri": "Estoque de CRI"}
                parts = [sub.get("_".join(rest), " ".join(rest).upper())]
            elif fam == "direcionamento":
                parts = [label, " ".join(rest).replace("_", " ")]
            elif fam == "imoveis":
                parts = ["Imóveis financiados", " ".join(rest).replace("_", " ")]
                unit = "R$" if "valor" in rest else ("m²" if "area" in rest else "unidades")
            else:
                parts = [" ".join(rest).upper().replace("_", " ")]
            return dict(series_id=base, name=" — ".join(p for p in parts if p), block=block, unit=unit, region=region)
    return None


def fetch_all(refresh: bool = True, first_year: int = 2014) -> list[dict]:
    """Baixa ano a ano: o serviço devolve HTTP 500 para páginas grandes sem filtro,
    mas responde em ~3 s a um ano inteiro (~25 mil linhas)."""
    import datetime as dt
    from urllib.parse import quote
    rows = []
    for year in range(first_year, dt.date.today().year + 1):
        # o OData do BCB exige %20 (rejeita '+' para espaço), por isso a URL é montada à mão
        flt = quote(f"Data ge '{year}-01-01' and Data le '{year}-12-31'")
        url = f"{BASE}?$format=json&$top={PAGE}&$filter={flt}"
        chunk = http.get_json(url, cache_name=f"bcb_olinda/{year}.json", refresh=refresh)["value"]
        rows.extend(chunk)
    return rows


def collect(refresh: bool = True):
    raw = fetch_all(refresh)
    out = []
    for r in raw:
        if r["Info"].lower().endswith("_na"):  # resíduo "não alocado" de 2014-15, sem UF
            continue
        d = _describe(r["Info"])
        if d is None or r["Valor"] is None:
            continue
        out.append({**d, "source": "bcb_olinda", "freq": "M", "date": r["Data"][:8] + "01", "value": r["Valor"]})
    df = store.frame(out)
    store.save(df, "bcb_olinda", {"url": BASE, "title": "BCB — Informações do Mercado Imobiliário",
                                  "coverage": "Brasil e UFs; SFN (todas as instituições)", "raw_rows": len(raw)})
    return df


if __name__ == "__main__":
    collect()
