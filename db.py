import os
import secrets
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

STATUS_VALIDOS = ("Solicitado", "Empenhado", "Não Empenhado", "Substituído")
STATUS_ATIVOS = ("Solicitado", "Empenhado")  # contam contra o saldo

SCHEMA = """
CREATE TABLE IF NOT EXISTS arps (
    numero_ata TEXT NOT NULL,
    uasg TEXT NOT NULL,
    numero_controle_pncp_ata TEXT,
    fornecedor TEXT,
    cnpj_fornecedor TEXT,
    data_vigencia_inicio TEXT,
    data_vigencia_fim TEXT,
    atualizado_em TEXT,
    PRIMARY KEY (numero_ata, uasg)
);

CREATE TABLE IF NOT EXISTS itens (
    numero_ata TEXT NOT NULL,
    uasg TEXT NOT NULL,
    numero_item TEXT NOT NULL,
    descricao TEXT,
    unidade TEXT,
    quantidade_homologada DOUBLE PRECISION DEFAULT 0,
    valor_unitario DOUBLE PRECISION DEFAULT 0,
    atualizado_em TEXT,
    PRIMARY KEY (numero_ata, uasg, numero_item)
);

CREATE TABLE IF NOT EXISTS empenhos (
    numero_ata TEXT NOT NULL,
    uasg TEXT NOT NULL,
    numero_item TEXT NOT NULL,
    quantidade_empenhada DOUBLE PRECISION DEFAULT 0,
    saldo_empenho DOUBLE PRECISION DEFAULT 0,
    atualizado_em TEXT,
    PRIMARY KEY (numero_ata, uasg, numero_item)
);

CREATE TABLE IF NOT EXISTS centros_custo (
    codigo TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    token TEXT UNIQUE
);

ALTER TABLE arps ADD COLUMN IF NOT EXISTS numero_compra TEXT;
ALTER TABLE arps ADD COLUMN IF NOT EXISTS ano_compra TEXT;
ALTER TABLE arps ADD COLUMN IF NOT EXISTS numero_controle_pncp_compra TEXT;
ALTER TABLE centros_custo ADD COLUMN IF NOT EXISTS ordem INTEGER;

CREATE TABLE IF NOT EXISTS pregoes_controle (
    numero_controle_pncp_compra TEXT NOT NULL,
    uasg TEXT NOT NULL,
    liberado BOOLEAN NOT NULL DEFAULT FALSE,
    prazo_final TEXT,
    atualizado_em TEXT,
    PRIMARY KEY (numero_controle_pncp_compra, uasg)
);

CREATE TABLE IF NOT EXISTS planejamento (
    id SERIAL PRIMARY KEY,
    numero_ata TEXT NOT NULL,
    uasg TEXT NOT NULL,
    numero_item TEXT NOT NULL,
    centro_custo TEXT NOT NULL,
    quantidade_planejada DOUBLE PRECISION NOT NULL DEFAULT 0,
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE (numero_ata, uasg, numero_item, centro_custo)
);

CREATE TABLE IF NOT EXISTS solicitacoes (
    id SERIAL PRIMARY KEY,
    centro_custo TEXT NOT NULL,
    data_solicitacao TEXT NOT NULL,
    nome_arquivo_pdf TEXT,
    conteudo_pdf BYTEA,
    observacao TEXT,
    criado_em TEXT
);

ALTER TABLE solicitacoes ADD COLUMN IF NOT EXISTS numero_controle_pncp_compra TEXT;
ALTER TABLE solicitacoes ADD COLUMN IF NOT EXISTS nome_arquivo_cessao TEXT;
ALTER TABLE solicitacoes ADD COLUMN IF NOT EXISTS conteudo_cessao_pdf BYTEA;

CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    solicitacao_id INTEGER REFERENCES solicitacoes(id),
    data_pedido TEXT NOT NULL,
    numero_ata TEXT NOT NULL,
    uasg TEXT NOT NULL,
    numero_item TEXT NOT NULL,
    centro_custo TEXT NOT NULL,
    quantidade_solicitada DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'Solicitado',
    criado_em TEXT,
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS pedidos_ajustes (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
    quantidade_anterior DOUBLE PRECISION NOT NULL,
    quantidade_nova DOUBLE PRECISION NOT NULL,
    observacao TEXT NOT NULL,
    criado_em TEXT
);
"""


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def novo_token():
    return secrets.token_urlsafe(16)


class Connection:
    """Fino wrapper para expor conn.execute(sql, params).fetchall()/.fetchone(),
    no mesmo estilo de sqlite3.Connection usado no restante do app."""

    def __init__(self, pg_conn):
        self._conn = pg_conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        return cur

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL não configurada. Defina a variável de ambiente (ou um arquivo .env) "
            "com a connection string do Postgres (ex.: obtida no Neon)."
        )
    pg_conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return Connection(pg_conn)


def init_db():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Schema do Postgres inicializado/atualizado.")
