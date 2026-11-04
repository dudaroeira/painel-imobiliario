"""Empacota o painel financeiro com senha para o site público (GitHub Pages).

    python -m financeiro.publicar

Lê dados/uau/painel/painel_financeiro.html, cifra o HTML inteiro com AES-256-GCM (chave derivada da senha por
PBKDF2-SHA256, 300 mil iterações, sal e nonce aleatórios) e grava dashboard/financeiro.html: uma página pequena
que pede a senha e, no navegador, deriva a chave e decifra o painel (WebCrypto). O que vai para o repositório e
para o site é só o texto cifrado; sem a senha não há como ler os dados.

A senha fica em dados/uau/painel/senha_site.txt (fora do git). Se o arquivo não existir, uma senha forte é gerada.
Trocar a senha = apagar o arquivo e rodar de novo (e avisar quem usa).
"""
from __future__ import annotations

import base64
import json
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

RAIZ = Path(__file__).resolve().parents[1]
PAINEL = RAIZ / "dados" / "uau" / "painel" / "painel_financeiro.html"
SENHA = RAIZ / "dados" / "uau" / "painel" / "senha_site.txt"
SAIDA = RAIZ / "dashboard" / "financeiro.html"
DESDE = "2025-01-01"  # o site mostra só o histórico a partir desta data
ITERACOES = 300_000

PALAVRAS = ("tijolo", "laje", "viga", "pilar", "obra", "torre", "sacada", "telhado", "janela", "portal", "alicerce",
            "fachada", "escada", "piso", "forro", "quadra", "lote", "marco", "ponte", "muro")


def gerar_senha() -> str:
    return "-".join(secrets.choice(PALAVRAS) for _ in range(4)) + "-" + str(secrets.randbelow(9000) + 1000)


def cifrar(html: str, senha: str) -> dict:
    sal, nonce = os.urandom(16), os.urandom(12)
    chave = PBKDF2HMAC(hashes.SHA256(), 32, sal, ITERACOES).derive(senha.encode("utf-8"))
    dados = AESGCM(chave).encrypt(nonce, html.encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return {"salt": b64(sal), "nonce": b64(nonce), "iter": ITERACOES, "data": b64(dados)}


PAGINA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Painel Financeiro · acesso restrito</title>
<style>
:root{--page:#f3f4f7;--surface:#fff;--ink:#15181e;--ink-2:#4b5563;--muted:#8a919c;--border:#e3e6eb;--accent:#2563eb;--accent-ink:#1d4ed8;--danger:#b91c1c}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--page:#0f1217;--surface:#1a1f29;--ink:#e8eaf0;--ink-2:#b3b9c6;--muted:#7c8494;--border:#2a3140;--accent:#60a5fa;--accent-ink:#93c5fd;--danger:#f87171}}
:root[data-theme="dark"]{--page:#0f1217;--surface:#1a1f29;--ink:#e8eaf0;--ink-2:#b3b9c6;--muted:#7c8494;--border:#2a3140;--accent:#60a5fa;--accent-ink:#93c5fd;--danger:#f87171}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;background:var(--page);color:var(--ink);font:15px/1.5 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
.card{width:100%;max-width:400px;background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:28px 24px}
h1{margin:0 0 4px;font-size:20px}
p{margin:0 0 18px;color:var(--ink-2)}
label{display:block;font-weight:600;margin-bottom:6px}
input{width:100%;padding:11px 12px;border:1px solid var(--border);border-radius:9px;background:var(--page);color:var(--ink);font:inherit}
input:focus{outline:2px solid var(--accent);outline-offset:1px}
button{margin-top:14px;width:100%;padding:11px;border:0;border-radius:9px;background:var(--accent);color:#fff;font:inherit;font-weight:600;cursor:pointer}
button[disabled]{opacity:.6;cursor:wait}
.erro{color:var(--danger);margin:10px 0 0;min-height:1.5em}
small{display:block;margin-top:16px;color:var(--muted)}
a{color:var(--accent-ink)}
</style>
</head>
<body>
<form class="card" id="f" autocomplete="off">
  <h1>Painel Financeiro</h1>
  <p>Acesso restrito. Os dados estão cifrados nesta página e só são lidos no seu navegador, com a senha.</p>
  <label for="s">Senha</label>
  <input id="s" type="password" autocomplete="current-password" autofocus required>
  <button id="b" type="submit">Abrir painel</button>
  <p class="erro" id="e" role="alert"></p>
  <small>Base de __DATA__. <a href="./">Voltar ao painel público</a></small>
</form>
<script>
const C = __CIFRADO__;
const u8 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
async function abrir(senha) {
  const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(senha), 'PBKDF2', false, ['deriveKey']);
  const chave = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: u8(C.salt), iterations: C.iter, hash: 'SHA-256' }, base,
    { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
  const claro = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: u8(C.nonce) }, chave, u8(C.data));
  return new TextDecoder().decode(claro);
}
document.getElementById('f').addEventListener('submit', async ev => {
  ev.preventDefault();
  const b = document.getElementById('b'), e = document.getElementById('e');
  b.disabled = true; e.textContent = '';
  try {
    const html = await abrir(document.getElementById('s').value);
    document.open(); document.write(html); document.close();
  } catch (x) {
    e.textContent = 'Senha incorreta.'; b.disabled = false;
    document.getElementById('s').select();
  }
});
</script>
</body>
</html>
"""


def publicar() -> Path:
    if not PAINEL.exists():
        raise SystemExit(f"Painel não encontrado: {PAINEL}. Rode python -m financeiro.atualizar antes.")
    if SENHA.exists():
        senha = SENHA.read_text(encoding="utf-8").strip()
    else:
        senha = gerar_senha()
        SENHA.write_text(senha + "\n", encoding="utf-8")
        print(f"Senha nova gerada em {SENHA}")
    from financeiro import painel
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        html = painel.gerar(destino=Path(tmp) / "painel_site.html", desde=DESDE).read_text(encoding="utf-8")
    data = "01/11/2026"
    import re
    m = re.search(r'"dataRef":"(\d{2}/\d{2}/\d{4})"', html)
    if m:
        data = m.group(1)
    pagina = PAGINA.replace("__CIFRADO__", json.dumps(cifrar(html, senha))).replace("__DATA__", data)
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(pagina, encoding="utf-8")
    print(f"{SAIDA} ({SAIDA.stat().st_size / 1e6:.1f} MB) · base de {data}")
    return SAIDA


if __name__ == "__main__":
    publicar()
