#!/usr/bin/env python3
"""TOP PROMO TITANIUM - bot de postagem de promoções no Telegram / WhatsApp.

Uso (no Termux ou terminal):
    export TELEGRAM_TOKEN="123456:ABC..."
    export TELEGRAM_CANAL="@toppromotitanium"   # opcional

    python bot.py              # posta até 5 produtos pendentes
    python bot.py 10           # posta até 10
    python bot.py teste        # mostra os textos sem enviar
    python bot.py whatsapp     # gera texto para colar no WhatsApp
    python bot.py adicionar    # adiciona produto perguntando campo a campo
    python bot.py listar       # lista produtos pendentes

Lê produtos.csv (colunas abaixo) e marca postado=sim depois de enviar.
"""
from __future__ import annotations

import csv
import html
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CANAL = os.environ.get("TELEGRAM_CANAL", "@toppromotitanium")
ARQUIVO = Path(os.environ.get("PRODUTOS_CSV", "produtos.csv"))
INTERVALO = 60  # segundos entre postagens (evita spam/limite do Telegram)

CAMPOS = ["loja", "titulo", "preco_de", "preco_por", "link", "imagem", "cupom", "postado"]


# ---------------------------------------------------------------------------
# Utilitários de CSV
# ---------------------------------------------------------------------------

def ler() -> list[dict]:
    if not ARQUIVO.exists():
        return []
    with ARQUIVO.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def salvar(linhas: list[dict]) -> None:
    with ARQUIVO.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows({c: (l.get(c) or "") for c in CAMPOS} for l in linhas)


def pendentes(linhas: list[dict] | None = None) -> list[dict]:
    if linhas is None:
        linhas = ler()
    return [l for l in linhas if (l.get("postado") or "").strip().lower() != "sim"]


# ---------------------------------------------------------------------------
# Formatação de preço (aceita 99,90 / 99.90 / R$ 99,90)
# ---------------------------------------------------------------------------

def normalizar_preco(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    v = re.sub(r"[R$\s]", "", v, flags=re.I)
    # "1.299,90" → "1299.90" | "1299,90" → "1299.90" | "1299.90" → "1299.90"
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    try:
        n = float(v)
        if n == int(n):
            return str(int(n))
        return f"{n:.2f}".rstrip("0").rstrip(".")
    except ValueError:
        return v


def url_ok(v: str) -> bool:
    return bool(re.match(r"^https?://", (v or "").strip(), re.I))


# ---------------------------------------------------------------------------
# Textos para Telegram e WhatsApp
# ---------------------------------------------------------------------------

def montar_texto(p: dict) -> str:
    linhas = [f"🔥 <b>{html.escape(p['titulo'])}</b>", ""]
    if p.get("preco_de"):
        linhas.append(f"❌ De: <s>R$ {html.escape(str(p['preco_de']))}</s>")
    linhas.append(f"✅ Por: <b>R$ {html.escape(str(p['preco_por']))}</b>")
    if p.get("cupom"):
        linhas.append(f"🎟 Cupom: <code>{html.escape(p['cupom'])}</code>")
    if p.get("loja"):
        linhas.append(f"🏪 {html.escape(p['loja'])}")
    linhas += ["", f"👉 {p['link']}", "", "⚠️ Preço e estoque podem mudar a qualquer momento."]
    return "\n".join(linhas)


def texto_whatsapp(p: dict) -> str:
    linhas = [f"🔥 *{p['titulo']}*", ""]
    if p.get("preco_de"):
        linhas.append(f"❌ De: ~R$ {p['preco_de']}~")
    linhas.append(f"✅ Por: *R$ {p['preco_por']}*")
    if p.get("cupom"):
        linhas.append(f"🎟 Cupom: {p['cupom']}")
    if p.get("loja"):
        linhas.append(f"🏪 {p['loja']}")
    linhas += ["", f"👉 {p['link']}"]
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Envio Telegram
# ---------------------------------------------------------------------------

def enviar(p: dict) -> bool:
    texto = montar_texto(p)
    base = f"https://api.telegram.org/bot{TOKEN}"
    if p.get("imagem") and len(texto) <= 1024:
        r = requests.post(
            f"{base}/sendPhoto",
            data={
                "chat_id": CANAL,
                "photo": p["imagem"],
                "caption": texto,
                "parse_mode": "HTML",
            },
            timeout=30,
        )
        if r.ok:
            return True
        print("Aviso foto:", r.status_code, r.text[:200])
    r = requests.post(
        f"{base}/sendMessage",
        data={
            "chat_id": CANAL,
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    if not r.ok:
        print("Erro:", r.status_code, r.text)
    return r.ok


# ---------------------------------------------------------------------------
# Modo adicionar (perguntas simples, sem |)
# ---------------------------------------------------------------------------

def perguntar(msg: str, obrigatorio: bool = True, default: str = "") -> str:
    while True:
        extra = f" [{default}]" if default else ""
        val = input(f"{msg}{extra}: ").strip()
        if not val and default:
            return default
        if val or not obrigatorio:
            return val
        print("  → campo obrigatório, digite algo.")


def modo_adicionar() -> None:
    print("\n=== Adicionar produto ===")
    print("(Enter vazio nos opcionais pula o campo)\n")

    loja = perguntar("Loja (Mercado Livre / Shopee / ...)", default="Mercado Livre")
    titulo = perguntar("Título do produto")
    preco_de = normalizar_preco(perguntar("Preço DE (riscado)", obrigatorio=False))
    preco_por = normalizar_preco(perguntar("Preço POR (atual)"))
    while True:
        link = perguntar("Link de afiliado (https://...)")
        if url_ok(link):
            break
        print("  → o link precisa começar com http:// ou https://")
    imagem = perguntar("URL da imagem (opcional)", obrigatorio=False)
    if imagem and not url_ok(imagem):
        print("  → imagem ignorada (não parece URL válida)")
        imagem = ""
    cupom = perguntar("Cupom (opcional)", obrigatorio=False)

    p = {
        "loja": loja,
        "titulo": titulo,
        "preco_de": preco_de,
        "preco_por": preco_por,
        "link": link,
        "imagem": imagem,
        "cupom": cupom,
        "postado": "",
    }

    print("\n--- Pré-visualização (Telegram) ---")
    print(montar_texto(p))
    print("-----------------------------------")

    conf = input("Salvar no produtos.csv? [S/n]: ").strip().lower()
    if conf in ("", "s", "sim", "y", "yes"):
        linhas = ler()
        linhas.append(p)
        salvar(linhas)
        print(f"✓ Salvo. Total de produtos: {len(linhas)} (pendentes: {len(pendentes(linhas))})")
        postar = input("Postar agora no Telegram? [s/N]: ").strip().lower()
        if postar in ("s", "sim", "y", "yes"):
            if not TOKEN:
                print("Defina TELEGRAM_TOKEN antes de postar.")
                return
            if enviar(p):
                p["postado"] = "sim"
                linhas[-1] = p
                salvar(linhas)
                print("✓ Postado no canal.")
            else:
                print("Falha ao postar. Produto ficou como pendente.")
    else:
        print("Cancelado, nada foi salvo.")


# ---------------------------------------------------------------------------
# Modo listar
# ---------------------------------------------------------------------------

def modo_listar() -> None:
    linhas = ler()
    pend = pendentes(linhas)
    print(f"Total: {len(linhas)} | Pendentes: {len(pend)} | Já postados: {len(linhas) - len(pend)}\n")
    for i, p in enumerate(pend, 1):
        preco = p.get("preco_por") or "?"
        print(f"{i:2}. [{p.get('loja','')}] {p.get('titulo','')[:55]}  → R$ {preco}")


# ---------------------------------------------------------------------------
# Modo WhatsApp
# ---------------------------------------------------------------------------

def modo_whatsapp() -> None:
    """Mostra o texto, copia para a área de transferência (se o Termux:API existir)."""
    linhas = ler()
    for p in pendentes(linhas):
        texto = texto_whatsapp(p)
        print("\n" + texto + "\n")
        try:
            subprocess.run(
                ["termux-clipboard-set"],
                input=texto.encode("utf-8"),
                check=True,
            )
            print("(texto copiado — é só colar no WhatsApp)")
        except Exception:
            print("(copie o texto acima manualmente)")
        r = input("Postou? s = marcar como postado | Enter = pular | q = sair: ").strip().lower()
        if r == "q":
            break
        if r == "s":
            p["postado"] = "sim"
            salvar(linhas)


# ---------------------------------------------------------------------------
# Modo principal (postar no Telegram)
# ---------------------------------------------------------------------------

def main() -> None:
    args = [a.lower() for a in sys.argv[1:]]

    if "adicionar" in args or "add" in args:
        return modo_adicionar()
    if "listar" in args or "lista" in args:
        return modo_listar()
    if "whatsapp" in args or "wa" in args:
        return modo_whatsapp()

    teste = "teste" in args
    numeros = [a for a in sys.argv[1:] if a.isdigit()]
    limite = int(numeros[0]) if numeros else 5

    if not teste and not TOKEN:
        sys.exit("Defina TELEGRAM_TOKEN antes (export TELEGRAM_TOKEN=...)")

    linhas = ler()
    pend = pendentes(linhas)
    if not pend:
        sys.exit("Nenhum produto pendente. Use: python bot.py adicionar")

    for i, p in enumerate(pend[:limite]):
        if teste:
            print(montar_texto(p), "\n" + "-" * 30)
            continue
        if enviar(p):
            p["postado"] = "sim"
            salvar(linhas)
            print("Postado:", (p.get("titulo") or "")[:60])
        else:
            print("Falhou:", (p.get("titulo") or "")[:60])
        if i < min(limite, len(pend)) - 1:
            time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
