"""Cadastra os centros de custo padrão do CEFET/RJ, na ordem usada nas telas de planejamento.
Idempotente: pode ser rodado de novo sem duplicar ou sem derrubar o token de quem já existe.
"""

import db

CENTROS_CUSTO = [
    ("DIREN", "DIREN"),
    ("DIPPG", "DIPPG"),
    ("DIREX", "DIREX"),
    ("DIREG", "DIREG"),
    ("DIGES", "DIGES"),
    ("DIRAP", "DIRAP"),
    ("DEPES", "DEPES"),
    ("DEMET", "DEMET"),
    ("PREF-MARACANA", "Prefeitura Maracanã"),
    ("MARIA-DA-GRACA", "Maria da Graça"),
    ("NOVA-IGUACU", "Nova Iguaçu"),
    ("PETROPOLIS", "Petrópolis"),
    ("NOVA-FRIBURGO", "Nova Friburgo"),
    ("ITAGUAI", "Itaguaí"),
    ("VALENCA", "Valença"),
    ("ANGRA-DOS-REIS", "Angra dos Reis"),
]


def seed():
    conn = db.get_conn()
    try:
        for ordem, (codigo, nome) in enumerate(CENTROS_CUSTO, start=1):
            conn.execute("""
                INSERT INTO centros_custo (codigo, nome, token, ordem)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo) DO UPDATE SET nome = excluded.nome, ordem = excluded.ordem
            """, (codigo, nome, db.novo_token(), ordem))
        conn.commit()
        print(f"{len(CENTROS_CUSTO)} centros de custo cadastrados/atualizados.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
