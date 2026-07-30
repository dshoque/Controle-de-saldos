# Controle de Saldos ARP — CEFET/RJ

Sistema web para controle descentralizado dos quantitativos das Atas de Registro de Preços (ARP) do CEFET/RJ, consolidando dados públicos da API do [Compras.gov.br](https://dadosabertos.compras.gov.br) com o planejamento interno por centro de custo (diretorias/campi).

## O problema que resolve

Cada centro de custo planeja os quantitativos que deseja para cada item de uma ARP. Na hora de pedir a entrega, é preciso conferir se ainda há saldo (planejado − já solicitado) antes de autorizar o pedido — e descontar da conta pedidos que depois não foram efetivamente empenhados. Até aqui esse controle era manual e centralizado (planilha + e-mail). Este sistema:

- Sincroniza automaticamente da API pública as atas, itens homologados e empenhos já realizados, incluindo o vínculo de cada ata com o pregão a que pertence (uma ata por lote/fornecedor vencedor do mesmo pregão).
- Deixa a DIARP decidir, pregão a pregão, quando ele fica aberto para pedidos e até qual prazo.
- Deixa cada centro de custo lançar seus próprios pedidos por um link individual, com verificação de saldo em tempo real — tanto o saldo do próprio centro quanto o saldo total do item na ata (somando todos os centros).
- Permite pedir acima do que o próprio centro planejou, desde que anexado um documento de cessão de outro centro de custo — nunca acima do que sobra fisicamente do item na ata, mesmo com cessão.
- Permite reenviar/corrigir um pedido antes do prazo: o envio anterior (ainda não decidido pela DIARP) é substituído, mantendo o histórico completo.
- Mantém o pedido assinado em PDF (e o de cessão, quando houver) como comprovante auditável, anexado a cada solicitação, para o processo administrativo.
- Rastreia o status de cada pedido (Solicitado → Empenhado / Não Empenhado / Substituído), recalculando o saldo disponível automaticamente conforme o status muda.
- Permite à DIARP corrigir manualmente a quantidade de um pedido quando ela diverge do PDF assinado, preservando o valor original, o novo valor e o motivo — visível para o centro de custo na própria página de acompanhamento dele.
- Confere periodicamente o total marcado como "Empenhado" internamente contra o total empenhado real, segundo a API.
- Gerencia o ciclo de vida dos dados: PDFs são expurgados um mês após o fim do prazo de um pregão; dados de atas com vigência encerrada ficam disponíveis para exportação em CSV e podem ser excluídos do sistema um mês depois — tudo disparado manualmente, sem depender de agendador externo.

## Por que substituir a planilha de controle

### Benefícios técnicos em relação ao modelo em planilha

Além da redução de erro humano e da centralização dos pedidos numa única plataforma, a migração do controle em Excel (uma aba por centro de custo, consolidada manualmente) para este sistema resolve limitações estruturais do modelo anterior:

| Limitação da planilha | Como o sistema resolve |
|---|---|
| Fórmula de saldo duplicada em cada aba (uma por centro de custo, mais as abas de consolidação) — qualquer ajuste no cálculo precisa ser replicado manualmente em todo lugar, sob risco de as abas divergirem entre si | Saldo calculado por uma única função (`calcular_saldos()` em `app.py`), usada por todas as telas — Saldos, Solicitação, Saldo por Pregão, Conferência. Estruturalmente não existe como duas telas mostrarem números diferentes para o mesmo item |
| Sem controle de concorrência: arquivo único, distribuído por e-mail/OneDrive, com risco de sobrescrita e de ambiguidade sobre qual é a versão vigente | Banco de dados relacional (Postgres) com transações e restrições de unicidade (ex.: um único registro de planejamento por item × centro de custo); vários centros de custo acessam ao mesmo tempo sem conflito |
| Sem trilha de auditoria: uma célula sobrescrita perde o valor anterior sem deixar rastro | Todo pedido carrega histórico de status (Solicitado → Empenhado/Substituído/Não Empenhado); quando a DIARP corrige uma quantidade divergente do PDF anexado, o valor anterior, o novo valor, o motivo e a data ficam registrados de forma permanente (tabela `pedidos_ajustes`) |
| Item, quantidade homologada e empenho digitados manualmente a partir de editais e PDFs — fonte clássica de erro de transcrição | Sincronização direta com a API de dados abertos do Compras.gov.br; os mesmos dados que a União já publica alimentam o sistema sem digitação manual |
| Validação de saldo é posterior — o excesso só é percebido quando alguém revisa a planilha consolidada | Validação em tempo real no momento da solicitação: o sistema bloqueia (ou exige o documento de cessão) antes de o pedido ser registrado, não depois |
| Cessão entre centros de custo combinada por e-mail, sem registro formal vinculado ao pedido | O documento de cessão é anexado dentro da própria solicitação, junto do PDF do pedido, com o mesmo controle de auditoria |
| Sem controle de acesso por centro de custo — quem tiver o arquivo vê e pode editar qualquer aba | Cada centro de custo recebe um link individual, restrito ao seu próprio planejamento; as telas administrativas exigem autenticação separada da DIARP |
| Disponibilidade depende de uma máquina ou pessoa específica (arquivo local ou anexo de e-mail) | Sistema hospedado e acessível a qualquer momento, independentemente de quem gerou a última cópia do arquivo |
| Sem controle de janela de tempo — nada impede um pedido fora de época, nem existe expiração de dados antigos | Prazo por pregão (bloqueia solicitação fora da janela) e ciclo de vida automático de PDFs/dados de atas encerradas, mantendo o volume de dados sob controle a longo prazo |

### Fundamentação legal — Lei nº 12.527/2011 (Lei de Acesso à Informação)

A disponibilização destes dados (planejamento, pedidos e saldo por ata de registro de preços) em formato de dados abertos encontra respaldo direto em dispositivos da LAI:

- **Art. 3º, II e III** — a Lei fixa como diretriz a "divulgação de informações de interesse público, independentemente de solicitações" e a "utilização de meios de comunicação viabilizados pela tecnologia da informação". Um painel de saldos publicamente consultável atende a isso de forma proativa, sem exigir que cada interessado apresente um pedido formal de acesso.
- **Art. 7º, VI** — garante o direito de obter "informação pertinente à administração do patrimônio público, utilização de recursos públicos, licitação, contratos administrativos" — categoria em que se enquadram diretamente os dados de execução de uma ata de registro de preços.
- **Art. 8º, *caput*** — impõe o dever de promover, "independentemente de requerimentos", a divulgação de informação de interesse coletivo produzida pelo órgão, o que inclui o controle de saldo e de pedidos de uma ARP.
- **Art. 8º, §3º, II** — exige que os sítios oficiais "possibilitem a gravação de relatórios em diversos formatos eletrônicos, inclusive abertos e não proprietários, tais como planilhas e texto" — já atendido pelas exportações em CSV implementadas em `/manutencao`.
- **Art. 8º, §3º, III** — exige "acesso automatizado por sistemas externos em formatos abertos, estruturados e legíveis por máquina". É o mesmo princípio que já rege a integração deste sistema com a API do Compras.gov.br (como consumidor de dados abertos); aplicar-se-ia, de forma simétrica, a uma futura exposição destes dados como fonte de dados abertos (como publicador).
- **Art. 4º, VI a IX** — define os atributos exigidos da informação pública: disponibilidade, autenticidade, integridade e primariedade. O modelo relacional com trilha de auditoria (ver tabela acima) atende a esses critérios de um modo que uma planilha compartilhada, por natureza, não garante.

Esses dispositivos fundamentam a conveniência e a aderência de publicar estes dados como abertos; a decisão sobre eventual classificação de sigilo e sobre o desenho final de uma publicação externa é análise jurídica/administrativa da própria DIARP, conforme os arts. 21 a 24 da mesma Lei.

## Como o fluxo funciona hoje

1. **Sincronizar** (`/`) — a DIARP atualiza atas, itens e empenhos a partir da API do Compras.gov.br.
2. **Planejar** — pontualmente em `/planejamento`, ou em lote por pregão inteiro (todos os itens de todas as suas atas, todos os centros de custo de uma vez) em `/planejamento/lote`.
3. **Liberar o pregão** — na mesma tela de planejamento em lote, a DIARP define se aquele pregão está aberto para solicitação e até qual prazo.
4. **Solicitar** — o centro de custo abre o próprio link (`/solicitar/<token>`), escolhe um pregão aberto, informa as quantidades desejadas e anexa o PDF assinado (e o de cessão, se estiver pedindo acima do que planejou). Pode reenviar e corrigir até o prazo.
5. **Acompanhar e decidir** — a DIARP acompanha tudo em `/pedidos`, muda o status de cada pedido (Empenhado / Não Empenhado) e, se notar divergência entre o valor lançado e o PDF anexado, corrige a quantidade com justificativa registrada.
6. **Conferir e visualizar** — `/conferencia` bate o total empenhado interno contra o real da API; `/saldo-pregao` mostra a mesma visão consolidada (item × centro de custo) que a DIARP já usava em planilha, agora por pregão.
7. **Arquivar** — em `/manutencao`, a DIARP expurga PDFs vencidos, exporta em CSV e eventualmente exclui dados de atas com vigência encerrada, e tira um backup completo de planejamento/pedidos quando quiser.

## Telas

| Tela | Acesso | O que faz |
|---|---|---|
| `/` (Saldos) | login DIARP | Painel com o saldo disponível por item × centro de custo |
| `/saldo-pregao` → `/saldo-pregao/<pregão>` | login DIARP | Saldo em formato de matriz (item nas linhas, centro de custo nas colunas) para um pregão específico — visão só leitura |
| `/planejamento` | login DIARP | Lançamento pontual de planejamento; cadastro dos centros de custo e link/token de cada um |
| `/planejamento/lote` → `/planejamento/lote/<pregão>` | login DIARP | Planejamento em lote de um pregão inteiro; liberação do pregão para solicitação e definição do prazo |
| `/novo-pedido` | login DIARP | Lançamento interno em lote via planilha `.xlsx` (ferramenta de apoio/backfill, sem PDF) |
| `/pedidos` | login DIARP | Histórico de pedidos, PDFs (pedido e cessão), mudança de status, correção de quantidade com auditoria |
| `/conferencia` | login DIARP | Compara o total "Empenhado" no controle interno com o total real da API |
| `/manutencao` | login DIARP | Expurgo de PDFs vencidos, exportação/exclusão de dados de atas com vigência encerrada, backup completo |
| `/solicitar/<token>` → `/solicitar/<token>/<pregão>` | link próprio do centro de custo, sem senha | Escolha do pregão e formulário de pedido (quantidades, PDF do pedido, PDF de cessão quando acima do plano) |
| `/solicitar/<token>/meus-pedidos` | link próprio do centro de custo, sem senha | Histórico dos próprios pedidos, incluindo correções feitas pela DIARP |

## Modelo de dados

| Tabela | O que guarda |
|---|---|
| `arps` | Atas sincronizadas da API, incluindo o vínculo com o pregão (`numero_compra`/`ano_compra`/`numero_controle_pncp_compra`) |
| `itens` | Itens de cada ata, com a quantidade homologada |
| `empenhos` | Quantidade empenhada por item, segundo a API |
| `centros_custo` | Diretorias/campi, cada um com token de acesso próprio e ordem de exibição |
| `planejamento` | Quantidade planejada por item × centro de custo |
| `pregoes_controle` | Se um pregão está liberado para solicitação e até qual prazo |
| `solicitacoes` | Cada envio de um centro de custo: PDF do pedido, PDF de cessão (quando houver), pregão de origem |
| `pedidos` | Cada linha de pedido: item, centro de custo, quantidade, status |
| `pedidos_ajustes` | Histórico de correções manuais de quantidade feitas pela DIARP (valor anterior, novo valor, motivo) |

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
python db.py              # cria/atualiza as tabelas no Postgres
python seed_centros.py    # cadastra os 16 centros de custo padrão (idempotente)
python app.py              # sobe em http://localhost:5057
```

## Sincronizando com a API

Pelo botão "Sincronizar com a API do Compras.gov.br" no painel de Saldos, ou via script:

```bash
python -c "import api_compras; print(api_compras.sincronizar('153010'))"
```

Busca as atas com vigência iniciada no último ano para a UASG informada (153010 = CEFET/RJ), os itens homologados e os empenhos já registrados — incluindo o pregão de origem de cada ata.

## Deploy (Render + Neon)

1. Criar um banco gratuito no Neon e copiar a `DATABASE_URL`.
2. Criar um Web Service no Render apontando para este repositório, com start command `gunicorn app:app` (já incluído no `Procfile`).
3. Configurar `DATABASE_URL`, `SECRET_KEY` e `ADMIN_PASSWORD` nas variáveis de ambiente do Render.
4. Rodar `python db.py` uma vez (ou deixar o `init_db()` do próprio `app.py` criar o schema no primeiro acesso), depois `python seed_centros.py`, e por fim sincronizar a API pelo painel.

## Estrutura

```
app.py                        # rotas Flask
db.py                          # conexão Postgres + schema
api_compras.py                 # cliente da API do Compras.gov.br
seed_centros.py                # cadastro inicial dos centros de custo (idempotente)
templates/                     # páginas Jinja
  base.html                       # layout comum das telas administrativas
  dashboard.html                  # Saldos
  saldo_pregao_lista.html         # Saldo por Pregão — lista
  saldo_pregao_grade.html         # Saldo por Pregão — matriz
  planejamento.html               # Planejamento pontual + centros de custo
  planejamento_lote_lista.html    # Planejamento em lote — lista de pregões + liberação
  planejamento_lote_grade.html    # Planejamento em lote — grade item × centro
  novo_pedido.html                # Lançamento interno via planilha
  pedidos.html                    # Histórico de pedidos + correção de quantidade
  conferencia.html                # Conferência com a API
  manutencao.html                 # Expurgo de PDF, CSV/exclusão de ata, backup
  solicitar_lista.html            # Picker de pregão (centro de custo)
  solicitar.html                  # Formulário de pedido por pregão (centro de custo)
  meus_pedidos.html               # Histórico do centro de custo
  login.html                      # Login da DIARP
requirements.txt
Procfile                       # start command de produção (gunicorn)
```
