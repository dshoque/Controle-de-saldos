import time

import psycopg2
import requests
from datetime import date, timedelta

import db

BASE = "https://dadosabertos.compras.gov.br/modulo-arp"
TIMEOUT = 30
TAMANHO_PAGINA = 500
ATRASO_ENTRE_CHAMADAS = 0.35  # segundos, evita 429 (Too Many Requests) na API pública
MAX_TENTATIVAS = 5


def _get(path, params):
    url = f"{BASE}/{path}"
    espera = 1.0
    ultimo_erro = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        resp = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=TIMEOUT)
        if resp.status_code == 429:
            ultimo_erro = requests.exceptions.HTTPError(f"429 Too Many Requests: {resp.url}")
            retry_after = resp.headers.get("Retry-After")
            time.sleep(float(retry_after) if retry_after else espera)
            espera *= 2
            continue
        resp.raise_for_status()
        time.sleep(ATRASO_ENTRE_CHAMADAS)
        return resp.json()
    raise ultimo_erro


def _paginado(path, params, tamanho_pagina=TAMANHO_PAGINA, max_paginas=200):
    resultados = []
    pagina = 1
    while pagina <= max_paginas:
        p = dict(params)
        p["pagina"] = pagina
        p["tamanhoPagina"] = tamanho_pagina
        data = _get(path, p)
        lote = data.get("resultado") if isinstance(data, dict) else data
        if not lote:
            break
        resultados.extend(lote)
        total_paginas = data.get("totalPaginas") if isinstance(data, dict) else None
        if total_paginas is not None and pagina >= total_paginas:
            break
        if total_paginas is None and len(lote) < tamanho_pagina:
            break
        pagina += 1
    return resultados


def janela_vigencia_padrao():
    hoje = date.today()
    return (hoje - timedelta(days=365)).isoformat(), hoje.isoformat()


def consultar_arps(uasg, data_min=None, data_max=None):
    if not data_min or not data_max:
        data_min, data_max = janela_vigencia_padrao()
    return _paginado("1_consultarARP", {
        "codigoUnidadeGerenciadora": uasg,
        "dataVigenciaInicialMin": data_min,
        "dataVigenciaInicialMax": data_max,
    })


def consultar_arp_itens(uasg, data_min=None, data_max=None):
    if not data_min or not data_max:
        data_min, data_max = janela_vigencia_padrao()
    return _paginado("2_consultarARPItem", {
        "codigoUnidadeGerenciadora": uasg,
        "dataVigenciaInicialMin": data_min,
        "dataVigenciaInicialMax": data_max,
    })


def consultar_empenhos_saldo(numero_ata, uasg):
    return _paginado("4_consultarEmpenhosSaldoItem", {
        "numeroAta": numero_ata,
        "unidadeGerenciadora": uasg,
    }, tamanho_pagina=100)


def sincronizar(uasg="153010"):
    """Atualiza as tabelas arps, itens e empenhos com os dados públicos da API do Compras.gov.br."""
    conn = db.get_conn()
    ts = db.agora()
    avisos = []
    try:
        arps = consultar_arps(uasg)
        for a in arps:
            numero_ata = str(a.get("numeroAtaRegistroPreco") or "").strip()
            if not numero_ata:
                continue
            conn.execute("""
                INSERT INTO arps (numero_ata, uasg, numero_controle_pncp_ata, fornecedor, cnpj_fornecedor,
                                   data_vigencia_inicio, data_vigencia_fim, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(numero_ata, uasg) DO UPDATE SET
                    numero_controle_pncp_ata=excluded.numero_controle_pncp_ata,
                    fornecedor=excluded.fornecedor,
                    cnpj_fornecedor=excluded.cnpj_fornecedor,
                    data_vigencia_inicio=excluded.data_vigencia_inicio,
                    data_vigencia_fim=excluded.data_vigencia_fim,
                    atualizado_em=excluded.atualizado_em
            """, (
                numero_ata, str(uasg),
                str(a.get("numeroControlePncpAta") or ""),
                a.get("objeto") or "",
                "",
                a.get("dataVigenciaInicial") or "",
                a.get("dataVigenciaFinal") or "",
                ts,
            ))

        itens = consultar_arp_itens(uasg)
        for i in itens:
            numero_ata = str(i.get("numeroAtaRegistroPreco") or "").strip()
            numero_item = str(i.get("numeroItem") or "").strip()
            if not numero_ata or not numero_item:
                continue
            conn.execute("""
                INSERT INTO itens (numero_ata, uasg, numero_item, descricao, unidade, quantidade_homologada, valor_unitario, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(numero_ata, uasg, numero_item) DO UPDATE SET
                    descricao=excluded.descricao,
                    unidade=excluded.unidade,
                    quantidade_homologada=excluded.quantidade_homologada,
                    valor_unitario=excluded.valor_unitario,
                    atualizado_em=excluded.atualizado_em
            """, (
                numero_ata, str(uasg), numero_item,
                i.get("descricaoItem") or "",
                i.get("nomeRazaoSocialFornecedor") or "",
                float(i.get("quantidadeHomologadaItem") or 0),
                float(i.get("valorUnitario") or 0),
                ts,
            ))
        conn.commit()

        atas = [row["numero_ata"] for row in
                conn.execute("SELECT DISTINCT numero_ata FROM arps WHERE uasg=%s", (str(uasg),)).fetchall()]

        for numero_ata in atas:
            try:
                empenhos = consultar_empenhos_saldo(numero_ata, uasg)
            except requests.exceptions.RequestException as e:
                avisos.append(f"Empenhos da ata {numero_ata}: falha ao consultar ({e})")
                continue

            # Reconecta se a conexão caiu por ociosidade durante as chamadas HTTP acima
            # (comum em Postgres serverless/pooled, como o Neon, quando a transação fica muito tempo sem tráfego).
            try:
                conn.execute("SELECT 1")
            except psycopg2.OperationalError:
                conn.close()
                conn = db.get_conn()

            for e in empenhos:
                # Mantém apenas o consumo da própria unidade gerenciadora (ignora adesões/caronas de outros órgãos).
                if e.get("tipo") not in (None, "GERENCIADORA"):
                    continue
                numero_item = str(e.get("numeroItem") or "").strip()
                if not numero_item:
                    continue
                conn.execute("""
                    INSERT INTO empenhos (numero_ata, uasg, numero_item, quantidade_empenhada, saldo_empenho, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT(numero_ata, uasg, numero_item) DO UPDATE SET
                        quantidade_empenhada=excluded.quantidade_empenhada,
                        saldo_empenho=excluded.saldo_empenho,
                        atualizado_em=excluded.atualizado_em
                """, (
                    numero_ata, str(uasg), numero_item,
                    float(e.get("quantidadeEmpenhada") or 0),
                    float(e.get("saldoEmpenho") or 0),
                    ts,
                ))
            # Commit por ata: mantém as transações curtas para não estourar timeouts de conexão ociosa.
            conn.commit()

        return {
            "quando": ts,
            "arps_sincronizadas": len(arps),
            "itens_sincronizados": len(itens),
            "atas_com_empenho_consultadas": len(atas),
            "avisos": avisos,
        }
    finally:
        conn.close()
