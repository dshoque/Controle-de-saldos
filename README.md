# Controle de Saldos ARP — CEFET/RJ

Sistema web para controle descentralizado dos quantitativos das Atas de Registro de Preços (ARP) do CEFET/RJ, consolidando dados públicos da API do [Compras.gov.br](https://dadosabertos.compras.gov.br) com o planejamento interno por centro de custo (diretorias/campi).

## O problema que resolve

Cada centro de custo planeja os quantitativos que deseja para cada item de uma ARP. Na hora de pedir a entrega, é preciso conferir se ainda há saldo (planejado − já solicitado) antes de autorizar o pedido — e descontar da conta pedidos que depois não foram efetivamente empenhados. Até aqui esse controle era manual e centralizado (planilha + e-mail). Este sistema:

- Sincroniza automaticamente da API pública as atas, itens homologados e empenhos já realizados.
- Deixa cada centro de custo lançar seus próprios pedidos por um link individual, com verificação de saldo em tempo real (não deixa enviar acima do planejado).
- Mantém o pedido assinado em PDF como comprovante auditável, anexado a cada solicitação, para o processo administrativo.
- Rastreia o status de cada pedido (Solicitado → Empenhado / Não Empenhado), recalculando o saldo disponível automaticamente quando um pedido não é empenhado.
- Confere periodicamente o total marcado como "Empenhado" internamente contra o total empenhado real, segundo a API.

## Telas

| Tela | Acesso | O que faz |
|---|---|---|
| `/` (Saldos) | login DIARP | Painel com o saldo disponível por item × centro de custo |
| `/planejamento` | login DIARP | Lançamento do quantitativo planejado por item/centro de custo; cadastro dos centros de custo e geração do link de cada um |
| `/pedidos` | login DIARP | Histórico de pedidos, PDF anexado, mudança de status |
| `/conferencia` | login DIARP | Compara o total empenhado no controle interno com o total real da API |
| `/solicitar/<token>` | link próprio do centro de custo, sem senha | Onde o solicitante lança as quantidades desejadas e anexa o PDF assinado |

## Stack

Flask + Postgres (via `psycopg2`), sem front-end framework (HTML + CSS + JS puro nos templates Jinja). Pensado para rodar num free tier (ex.: [Render](https://render.com) + [Neon](https://neon.tech)).

## Configuração

Variáveis de ambiente necessárias (num arquivo `.env` local, ou nas variáveis de ambiente do host em produção):

```
DATABASE_URL=postgresql://usuario:senha@host/banco?sslmode=require
SECRET_KEY=uma-string-aleatoria-longa
ADMIN_PASSWORD=senha-da-equipe-diarp
```

`DATABASE_URL` é a connection string do Postgres (ex.: fornecida pelo Neon). `SECRET_KEY` assina a sessão do Flask — gere uma nova com `python -c "import secrets; print(secrets.token_hex(32))"`. `ADMIN_PASSWORD` é a senha única de acesso às telas administrativas.

## Rodando localmente

```bash
pip install -r requirements.txt
python db.py        # cria/atualiza as tabelas no Postgres
python app.py        # sobe em http://localhost:5057
```

## Sincronizando com a API

Pelo botão "Sincronizar com a API do Compras.gov.br" no painel de Saldos, ou via script:

```bash
python -c "import api_compras; print(api_compras.sincronizar('153010'))"
```

Busca as atas com vigência iniciada no último ano para a UASG informada (153010 = CEFET/RJ), os itens homologados e os empenhos já registrados.

## Deploy (Render + Neon)

1. Criar um banco gratuito no Neon e copiar a `DATABASE_URL`.
2. Criar um Web Service no Render apontando para este repositório, com start command `gunicorn app:app` (já incluído no `Procfile`).
3. Configurar `DATABASE_URL`, `SECRET_KEY` e `ADMIN_PASSWORD` nas variáveis de ambiente do Render.
4. Rodar `python db.py` uma vez (ou deixar o `init_db()` do próprio `app.py` criar o schema no primeiro acesso) e depois sincronizar a API pelo painel.

## Estrutura

```
app.py              # rotas Flask
db.py                # conexão Postgres + schema
api_compras.py       # cliente da API do Compras.gov.br
templates/            # páginas Jinja
requirements.txt
Procfile              # start command de produção (gunicorn)
```
