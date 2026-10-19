"""Cliente HTTP com cache em data/raw e User-Agent de navegador (alguns sites bloqueiam o UA padrão)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import requests

from .store import RAW

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) painel-imobiliario/0.1"
TIMEOUT = 120


def get(url: str, *, params: dict | None = None, cache_name: str | None = None, refresh: bool = False, **kw) -> bytes:
    """GET com cache em disco. `cache_name` fixa o nome do arquivo (ex.: 'secovi/202608-pmi.pdf');
    sem ele, usa um hash da URL. `refresh=True` ignora o cache."""
    if cache_name is None:
        cache_name = "http/" + hashlib.sha1((url + str(params or "")).encode()).hexdigest()[:16]
    path = RAW / cache_name
    if path.exists() and not refresh:
        return path.read_bytes()
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.content


def get_json(url: str, **kw):
    import json
    return json.loads(get(url, **kw).decode("utf-8"))


def exists(url: str) -> bool:
    try:
        r = requests.head(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
        return r.status_code == 200
    except requests.RequestException:
        return False
