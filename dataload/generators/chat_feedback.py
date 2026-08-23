"""Gerador de avaliações vinculadas a sessões existentes."""

import random
from datetime import datetime, timedelta, timezone

from dataload.mongo_client import obter_colecao


class SemSessoesChatError(RuntimeError):
    """Indica que não existem sessões que possam receber feedback."""


def gerar(quantidade: int) -> list[dict]:
    """Gera feedbacks usando somente IDs reais de chat_sessions."""
    chat_sessions = obter_colecao("db_delta_app", "chat_sessions")
    session_ids = [sessao["_id"] for sessao in chat_sessions.find({}, {"_id": 1})]

    if not session_ids:
        raise SemSessoesChatError(
            "nenhuma sessão foi encontrada em db_delta_app.chat_sessions. "
            "Rode 'python -m dataload.cli chat_sessions <n>' primeiro."
        )

    agora = datetime.now(timezone.utc).replace(microsecond=0)
    comentarios = [
        "A resposta resolveu minha dúvida.",
        "A explicação poderia ter mais detalhes.",
        "Consegui entender melhor meu consumo.",
        None,
    ]

    return [
        {
            "session_id": random.choice(session_ids),
            "is_satisfied": random.choice([True, False]),
            "user_comment": random.choice(comentarios),
            "created_at": agora - timedelta(minutes=indice),
        }
        for indice in range(quantidade)
    ]
