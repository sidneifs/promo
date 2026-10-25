#!/usr/bin/env python3
"""TOP PROMO TITANIUM - busca as melhores ofertas da Shopee e grava no produtos.csv.

Usa a API oficial de afiliados da Shopee (Open API). Antes, defina no Termux:
    export SHOPEE_APP_ID="seu_app_id"
    export SHOPEE_SECRET="seu_secret"

Uso:
    python atualizar_shopee.py teste   # só mostra o que encontrou, não grava
    python atualizar_shopee.py         # grava as ofertas novas no produtos.csv
    python atualizar_shopee.py 5       # quantidade diferente de 10
"""
import csv
import hashlib
import json
import os
import sys
import time

import requests

URL = "https://open-api.affiliate.shopee.com.br/graphql"
APP_ID = os.environ.get("SHOPEE_APP_ID", "")
SECRET = os.environ.get("SHOPEE_SECRET", "")
ARQUIVO = os.environ.get("PRODUTOS_CSV", "produtos.csv")

QUANTIDADE = 10        # quantas ofertas gravar
DESCONTO_MINIMO = 20   # só entram produtos com pelo menos esse % de desconto
BUSCA = 50             # quantos pedir à API antes de filtrar
ORDEM = 2              # 1 relevância | 2 mais vendidos | 3 maior preço | 4 menor preço | 5 maior comissão

CAMPOS = ["loja", "titulo", "preco_de", "preco_por", "link", "imagem", "cupom", "postado"]

CONSULTA = (
    "query { productOfferV2(sortType: ORDEM, limit: BUSCA, page: 1) { nodes { "
    "itemId productName imageUrl priceMin priceMax priceDiscountRate offerLink sales ratingStar "
    "} } }"
)


def chamar_api(consulta):
    corpo = json.dumps({"query": consulta}, separators=(",", ":"))
    ts = str(int(time.time()))
    assinatura = hashlib.sha256((APP_ID + ts + corpo + SECRET).encode("utf-8")).hexdigest()
    cab = {
        "Authorization": f"SHA256 Credential={APP_ID}, Timestamp={ts}, Signature={assinatura}",
        "Content-Type": "application/json",
    }
    r = requests.post(URL, data=corpo, headers=cab, timeout=30)
    try:
        dados = r.json()
    except ValueError:
        sys.exit(f"Resposta inesperada ({r.status_code}): {r.text[:300]}")
    if dados.get("errors"):
        sys.exit("A Shopee devolveu erro: " + json.dumps(dados["errors"], ensure_ascii=False)[:500])
    return dados


def br(n):
    return f"{n:.2f}".replace(".", ",")


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return 0.0


def converter(no):
    """Transforma um produto da API em uma linha do produtos.csv (ou None se não servir)."""
    por = num(no.get("priceMin"))
    desc = num(no.get("priceDiscountRate"))
    link = (no.get("offerLink") or "").strip()
    if por <= 0 or not link or desc < DESCONTO_MINIMO or desc >= 95:
        return None
    de = round(por / (1 - desc / 100), 2)
    return {
        "loja": "Shopee",
        "titulo": (no.get("productName") or "Oferta Shopee").strip(),
        "preco_de": br(de),
        "preco_por": br(por),
        "link": link,
        "imagem": (no.get("imageUrl") or "").strip(),
        "cupom": "",
        "postado": "",
    }


def ler_csv():
    if not os.path.exists(ARQUIVO):
        return []
    with open(ARQUIVO, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def gravar_csv(linhas):
    with open(ARQUIVO, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows({c: l.get(c, "") for c in CAMPOS} for l in linhas)


def main():
    teste = "teste" in sys.argv[1:]
    nums = [a for a in sys.argv[1:] if a.isdigit()]
    quantidade = int(nums[0]) if nums else QUANTIDADE

    if not APP_ID or not SECRET:
        sys.exit("Defina SHOPEE_APP_ID e SHOPEE_SECRET antes (veja o início deste arquivo).")

    consulta = CONSULTA.replace("ORDEM", str(ORDEM)).replace("BUSCA", str(BUSCA))
    nos = chamar_api(consulta)["data"]["productOfferV2"]["nodes"]

    existentes = ler_csv()
    ja_tem = {l.get("link", "").strip() for l in existentes}
    novas = []
    for no in nos:
        linha = converter(no)
        if linha and linha["link"] not in ja_tem:
            novas.append(linha)
            ja_tem.add(linha["link"])
        if len(novas) >= quantidade:
            break

    print(f"A API devolveu {len(nos)} produtos; {len(novas)} entram (desconto mínimo {DESCONTO_MINIMO}%).")
    for l in novas:
        print(f"- {l['titulo'][:60]} | de R$ {l['preco_de']} por R$ {l['preco_por']}")
    if teste or not novas:
        return
    gravar_csv(existentes + novas)
    print(f"Gravado em {ARQUIVO}. Total de linhas: {len(existentes) + len(novas)}")


if __name__ == "__main__":
    main()
