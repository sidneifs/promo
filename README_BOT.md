# TOP PROMO TITANIUM — bot + landing page

## Arquivos importantes

| Arquivo        | Função                                      |
|----------------|---------------------------------------------|
| `produtos.csv` | Lista de produtos (mesmo arquivo do site)   |
| `bot.py`       | Posta no Telegram / gera texto WhatsApp     |
| `index.html`   | Landing page (lê o produtos.csv automaticamente) |

## Como usar o bot

No Termux (ou qualquer terminal com Python 3):

```bash
export TELEGRAM_TOKEN="SEU_TOKEN_AQUI"
# opcional:
export TELEGRAM_CANAL="@toppromotitanium"

python bot.py adicionar   # adiciona produto (perguntas simples)
python bot.py listar      # vê o que está pendente
python bot.py             # posta até 5 pendentes
python bot.py 10          # posta até 10
python bot.py teste       # só mostra o texto, não envia
python bot.py whatsapp    # gera texto para colar no WhatsApp
```

### Adicionar produto (sem usar |)

```
$ python bot.py adicionar

=== Adicionar produto ===
Loja (Mercado Livre / Shopee / ...) [Mercado Livre]: Shopee
Título do produto: Kit Gamer RGB
Preço DE (riscado): 99,90
Preço POR (atual): 54,99
Link de afiliado (https://...): https://s.shopee.com.br/xxxxx
URL da imagem (opcional): https://...
Cupom (opcional):

--- Pré-visualização ---
...
Salvar no produtos.csv? [S/n]: s
Postar agora no Telegram? [s/N]: s
```

Preços aceitam `99,90`, `99.90` ou `R$ 99,90`.

## Atualizar a landing page

1. Substitua o `produtos.csv` no repositório GitHub (tem que ser **CSV texto UTF-8**, não Excel).
2. Espere 1–2 minutos.
3. Abra https://sidneifs.github.io/promo/ (Ctrl+F5 se precisar).

A página mostra os **últimos 24 produtos** do CSV (as linhas finais).

## Observações

- O campo `postado` fica vazio até o bot marcar `sim`.
- A landing page **ignora** a coluna `postado` e a coluna `cupom` (só usa loja, titulo, preços, link, imagem).
- Se o `produtos.csv` no GitHub for um arquivo Excel, a página cai na lista de reserva (sem imagens).
