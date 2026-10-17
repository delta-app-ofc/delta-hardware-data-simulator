"""Sessões por usuário/dia com durações individuais dos especialistas."""

from datetime import timedelta
from itertools import islice

from dataload.context import aleatorio, exemplo, horario, identificador

AGENTES = ("consumption", "forecast", "leak")
CONVERSAS = (
    ("Como está meu consumo?", "Consulte seu consumo e a meta diária no aplicativo."),
    ("Qual a previsão de consumo?", "A previsão considera seu histórico de consumo."),
    (
        "Há algum vazamento?",
        "Confira os alertas e verifique os pontos de uso do imóvel.",
    ),
)


def gerar_periodo(cenario):
    for dia in cenario.dias():
        for usuario in cenario.usuarios():
            if not any(
                d["user_id"] == usuario and cenario.ativo(d, dia)
                for d in cenario.dispositivos
            ):
                continue
            mensagens = []
            inicio = horario(dia, 12)
            for indice, agente in enumerate(AGENTES):
                sorteio = aleatorio(cenario.seed, "chamada", usuario, dia, agente)
                pergunta, resposta = CONVERSAS[indice]
                duracao = int(sorteio.lognormvariate(7.1 + indice * 0.15, 0.5))
                if sorteio.random() < 0.04:
                    duracao *= 4  # Outliers positivos para a distribuição do boxplot.
                falha = sorteio.random() < 0.15
                status = sorteio.choice((429, 500, 503)) if falha else 200
                enviada = inicio + timedelta(minutes=indice * 3)
                mensagens.extend(
                    [
                        {
                            "role": "user",
                            "content_type": "text",
                            "content": pergunta,
                            "sent_at": enviada,
                            "api_status_code": 200,
                        },
                        {
                            "role": "bot",
                            "content_type": "text",
                            "content": (
                                "Falha técnica simulada; tente novamente."
                                if falha
                                else resposta
                            ),
                            "sent_at": enviada + timedelta(milliseconds=duracao),
                            "api_status_code": status,
                            "agent_name": agente,
                            "response_time_ms": duracao,
                        },
                    ]
                )
            yield {
                "_id": identificador("chat_sessions", usuario, dia),
                "user_id": usuario,
                "started_at": inicio,
                "last_activity_at": mensagens[-1]["sent_at"],
                "is_open": False,
                "is_active": False,
                "is_deleted": False,
                "messages": mensagens,
            }


def gerar(quantidade: int) -> list[dict]:
    return list(islice(gerar_periodo(exemplo()), quantidade))
