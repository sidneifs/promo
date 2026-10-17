#!/usr/bin/env python3
"""TOP PROMO TITANIUM - bot de postagem de promoções no Telegram.

Uso (no Termux):
    export TELEGRAM_TOKEN="123456:ABC..."
    python bot.py          # posta até 5 produtos pendentes
    python bot.py 10       # posta até 10
    python bot.py teste    # mostra os textos sem enviar
    python bot.py whatsapp # gera o texto de cada produto para colar no WhatsApp

Lê produtos.csv (colunas abaixo) e marca postado=sim depois de enviar.
"""
import csv
import html
import os
import subprocess
import sys
import time

import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CANAL = os.environ.get("TELEGRAM_CANAL", "@toppromotitanium")
ARQUIVO = os.environ.get("PRODUTOS_CSV", "produtos.csv")
INTERVALO = 60  # segundos entre postagens (evita spam/limite do Telegram)

CAMPOS = ["loja", "titulo", "preco_de", "preco_por", "link", "imagem", "cupom", "postado"]


def montar_texto(p):
    linhas = [f"🔥 <b>{html.escape(p['titulo'])}</b>", ""]
    if p.get("preco_de"):
        linhas.append(f"❌ De: <s>R$ {html.escape(p['preco_de'])}</s>")
    linhas.append(f"✅ Por: <b>R$ {html.escape(p['preco_por'])}</b>")
    if p.get("cupom"):
        linhas.append(f"🎟 Cupom: <code>{html.escape(p['cupom'])}</code>")
    if p.get("loja"):
        linhas.append(f"🏪 {html.escape(p['loja'])}")
    linhas += ["", f"👉 {p['link']}", "", "⚠️ Preço e estoque podem mudar a qualquer momento."]
    return "\n".join(linhas)


def enviar(p):
    texto = montar_texto(p)
    base = f"https://api.telegram.org/bot{TOKEN}"
    if p.get("imagem") and len(texto) <= 1024:
        r = requests.post(
            f"{base}/sendPhoto",
            data={"chat_id": CANAL, "photo": p["imagem"], "caption": texto, "parse_mode": "HTML"},
            timeout=30,
        )
        if r.ok:
            return True
    r = requests.post(
        f"{base}/sendMessage",
        data={"chat_id": CANAL, "text": texto, "parse_mode": "HTML"},
        timeout=30,
    )
    if not r.ok:
        print("Erro:", r.status_code, r.text)
    return r.ok


def ler():
    with open(ARQUIVO, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def salvar(linhas):
    with open(ARQUIVO, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows({c: l.get(c, "") for c in CAMPOS} for l in linhas)


def texto_whatsapp(p):
    linhas = [f"🔥 *{p['titulo']}*", ""]
    if p.get("preco_de"):
        linhas.append(f"❌ De: ~R$ {p['preco_de']}~")
    linhas.append(f"✅ Por: *R$ {p['preco_por']}*")
    if p.get("cupom"):
        linhas.append(f"🎟 Cupom: {p['cupom']}")
    linhas += ["", f"👉 {p['link']}"]
    return "\n".join(linhas)


def modo_whatsapp():
    """Mostra o texto, copia para a área de transferência (se o Termux:API existir)."""
    linhas = ler()
    for p in linhas:
        if p.get("postado", "").strip().lower() == "sim":
            continue
        texto = texto_whatsapp(p)
        print("\n" + texto + "\n")
        try:
            subprocess.run(["termux-clipboard-set"], input=texto.encode("utf-8"), check=True)
            print("(texto copiado - é só colar no WhatsApp)")
        except Exception:
            print("(copie o texto acima manualmente)")
        r = input("Postou? s = marcar como postado | Enter = pular | q = sair: ").strip().lower()
        if r == "q":
            break
        if r == "s":
            p["postado"] = "sim"
            salvar(linhas)


def main():
    if "whatsapp" in sys.argv[1:]:
        return modo_whatsapp()
    teste = "teste" in sys.argv[1:]
    numeros = [a for a in sys.argv[1:] if a.isdigit()]
    limite = int(numeros[0]) if numeros else 5

    if not teste and not TOKEN:
        sys.exit("Defina TELEGRAM_TOKEN antes (export TELEGRAM_TOKEN=...)")

    linhas = ler()
    pendentes = [l for l in linhas if l.get("postado", "").strip().lower() != "sim"]
    if not pendentes:
        sys.exit("Nenhum produto pendente.")

    for i, p in enumerate(pendentes[:limite]):
        if teste:
            print(montar_texto(p), "\n" + "-" * 30)
            continue
        if enviar(p):
            p["postado"] = "sim"
            salvar(linhas)  # salva a cada envio, não perde progresso
            print("Postado:", p["titulo"][:50])
        if i < min(limite, len(pendentes)) - 1:
            time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
