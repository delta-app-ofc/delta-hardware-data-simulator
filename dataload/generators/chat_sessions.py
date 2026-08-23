"""Gerador de sessões e mensagens do chatbot."""

import random
from datetime import datetime, timedelta, timezone


CONVERSAS = [
    (
        "Como está meu consumo de água hoje?",
        "Seu consumo está dentro da meta diária configurada.",
    ),
    (
        "O que significa o alerta de fluxo atípico?",
        "Ele indica um consumo diferente do padrão recente do imóvel.",
    ),
    (
        "Como posso reduzir meu consumo?",
        "Verifique vazamentos e evite deixar torneiras abertas sem necessidade.",
    ),
]


def gerar(quantidade: int) -> list[dict]:
    """Gera sessões com uma pergunta e uma resposta em ordem cronológica."""
    agora = datetime.now(timezone.utc).replace(microsecond=0)
    documentos = []

    for indice in range(quantidade):
        pergunta, resposta = random.choice(CONVERSAS)
        started_at = agora - timedelta(minutes=(quantidade - indice) * 10)
        pergunta_enviada_em = started_at + timedelta(seconds=5)
        resposta_enviada_em = started_at + timedelta(seconds=12)
        is_open = random.choice([True, False])

        documentos.append(
            {
                "user_id": random.randint(1, 1_000_000),
                "started_at": started_at,
                "last_activity_at": resposta_enviada_em,
                "is_open": is_open,
                "is_active": is_open and random.choice([True, False]),
                "is_deleted": False,
                "messages": [
                    {
                        "role": "user",
                        "content_type": "text",
                        "content": pergunta,
                        "sent_at": pergunta_enviada_em,
                        "api_status_code": 200,
                    },
                    {
                        "role": "bot",
                        "content_type": "text",
                        "content": resposta,
                        "sent_at": resposta_enviada_em,
                        "api_status_code": 200,
                    },
                ],
            }
        )

    return documentos
