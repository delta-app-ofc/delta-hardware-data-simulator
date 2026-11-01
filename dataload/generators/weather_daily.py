"""Clima sintético horário no mesmo calendário e nas mesmas cidades do SQL."""

import math
from itertools import islice
import random
from datetime import datetime, timedelta, timezone
from dataload.context import aleatorio, exemplo, horario, identificador


CONDICOES = ("Clear", "Clouds", "Rain")


def observacao(local: dict, dia, hora: int, seed: int) -> dict:
    sorteio = aleatorio(seed, "clima", local["city"], dia, hora)
    ciclo_dias = 7 * math.sin(dia.toordinal() * 2 * math.pi / 19)
    ciclo_horas = 5 * math.cos((hora - 14) * 2 * math.pi / 24)
    latitude = local.get("latitude")
    variacao_local = (
        (latitude + 23) * 0.7
        if latitude is not None
        else aleatorio(seed, "clima-base", local["city"]).uniform(-2, 2)
    )
    temperatura = round(
        23 + ciclo_dias + ciclo_horas + variacao_local + sorteio.uniform(-1, 1),
        2,
    )
    umidade = round(
        max(25, min(98, 72 - ciclo_horas * 3 + sorteio.uniform(-10, 10))), 1
    )
    vento = round(sorteio.uniform(0.2, 6), 2)
    chuva = (
        round(sorteio.uniform(0.2, 8), 2)
        if umidade > 78 and sorteio.random() < 0.35
        else 0.0
    )
    return {
        "hour": hora,
        "observed_at": horario(dia, hora),
        "temperature_c": float(temperatura),
        "feels_like_c": float(
            round(
                temperatura + max(0, temperatura - 24) * umidade / 100 - vento * 0.25, 2
            )
        ),
        "humidity_percent": umidade,
        "rain_mm": chuva,
        "wind_speed_mps": vento,
        "condition": "Rain" if chuva else "Clouds" if umidade > 70 else "Clear",
    }


def gerar_periodo(cenario):
    for dia in cenario.dias():
        for local in cenario.locais():
            horas = [observacao(local, dia, hora, cenario.seed) for hora in range(24)]
            yield {
                "_id": identificador("weather_daily", local["city"], dia),
                "location": {
                    "city": local["city"],
                    "state": local["state"],
                    "country": "BR",
                },
                "weather_date": horario(dia),
                "hours": horas,
                "samples": len(horas),
                "created_at": horario(dia),
                "updated_at": horas[-1]["observed_at"],
            }


def gerar(quantidade: int) -> list[dict]:
    return list(islice(gerar_periodo(exemplo()), quantidade))
"""Gerador de observações meteorológicas diárias."""



def gerar(quantidade: int) -> list[dict]:
    """Gera um documento por dia, com 24 observações horárias ordenadas."""
    hoje = datetime.now(timezone.utc).date()
    documentos = []

    for indice in range(quantidade):
        dia = hoje - timedelta(days=indice + 1)
        inicio_do_dia = datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)
        horas = []

        for hora in range(24):
            observado_em = inicio_do_dia + timedelta(hours=hora)
            temperatura = round(random.uniform(12.0, 32.0), 1)
            vento = round(random.uniform(0.0, 8.0), 1)

            horas.append(
                {
                    "hour": hora,
                    "observed_at": observado_em,
                    "temperature_c": temperatura,
                    "feels_like_c": round(temperatura + random.uniform(-2, 2), 1),
                    "humidity_percent": random.randint(25, 100),
                    "pressure_hpa": round(random.uniform(990.0, 1035.0), 1),
                    "rain_mm": round(random.uniform(0.0, 8.0), 1),
                    "cloud_coverage_percent": random.randint(0, 100),
                    "wind_speed_m_s": vento,
                    "wind_gust_m_s": round(vento + random.uniform(0, 5), 1),
                    "condition": random.choice(CONDICOES),
                }
            )

        documentos.append(
            {
                "location": {
                    "city": "São Paulo",
                    "state": "SP",
                    "country": "BR",
                },
                "date": inicio_do_dia,
                "hours": horas,
                "samples": len(horas),
                "created_at": inicio_do_dia + timedelta(minutes=1),
                "updated_at": inicio_do_dia + timedelta(hours=23, minutes=1),
            }
        )

    return documentos
