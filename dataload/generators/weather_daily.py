"""Clima sintético horário no mesmo calendário e nas mesmas cidades do SQL."""

import math
from itertools import islice

from dataload.context import aleatorio, exemplo, horario, identificador


def observacao(local: dict, dia, hora: int, seed: int) -> dict:
    sorteio = aleatorio(seed, "clima", local["city"], dia, hora)
    ciclo_dias = 7 * math.sin(dia.toordinal() * 2 * math.pi / 19)
    ciclo_horas = 5 * math.cos((hora - 14) * 2 * math.pi / 24)
    temperatura = round(
        23
        + ciclo_dias
        + ciclo_horas
        + (local["latitude"] + 23) * 0.7
        + sorteio.uniform(-1, 1),
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
