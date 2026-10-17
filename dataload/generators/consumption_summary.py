"""Consumo em janelas completas de cinco minutos, ligado ao cadastro SQL."""

from datetime import timedelta
from itertools import islice

from dataload.context import aleatorio, exemplo, horario, identificador
from dataload.generators.profiles import base_diaria, eventos_do_dia
from dataload.generators.weather_daily import observacao


def gerar_periodo(cenario):
    locais = {local["city"]: local for local in cenario.locais()}
    for dia in cenario.dias():
        for dispositivo in cenario.dispositivos:
            if not cenario.ativo(dispositivo, dia):
                continue
            residencial = dispositivo["classification_group"] == "RESIDENCIAL"
            pesos = (
                [
                    2.7 if h in (6, 7, 8, 18, 19, 20) else 0.25 if h < 5 else 0.8
                    for h in range(24)
                ]
                if residencial
                else [2.2 if 8 <= h < 18 else 0.15 for h in range(24)]
            )
            normalizador = sum(pesos) / 24
            eventos = eventos_do_dia(dispositivo, dia, cenario.seed)
            variacao = aleatorio(
                cenario.seed, "dia", dispositivo["device_id"], dia
            ).uniform(0.75, 1.25)
            semana = 0.35 if not residencial and dia.weekday() >= 5 else 1.0
            base = base_diaria(dispositivo, cenario)
            for hora in range(24):
                temperatura = observacao(
                    locais[dispositivo["city"]], dia, hora, cenario.seed
                )["temperature_c"]
                clima = max(0.6, 1 + (temperatura - 23) * 0.035)
                for minuto in range(0, 60, 5):
                    inicio = horario(dia, hora) + timedelta(minutes=minuto)
                    sorteio = aleatorio(
                        cenario.seed, "janela", dispositivo["device_id"], inicio
                    )
                    litros = (
                        base
                        / 288
                        * pesos[hora]
                        / normalizador
                        * clima
                        * variacao
                        * semana
                        * sorteio.uniform(0.7, 1.3)
                    )
                    atipico = eventos["fluxo_atipico"] and hora == 10
                    if atipico:
                        litros *= 3
                    vazando = eventos["vazamento_continuo"] and hora < 6
                    if vazando:
                        litros += 1.5
                    litros = float(round(litros, 4))
                    yield {
                        "_id": identificador(
                            "consumption_summary", dispositivo["device_id"], inicio
                        ),
                        "device_id": dispositivo["device_id"],
                        "user_id": dispositivo["user_id"],
                        "window_started_at": inicio,
                        "window_finished_at": inicio + timedelta(minutes=5),
                        "consumption_liters": litros,
                        "lpm_average": float(round(litros / 5, 6)),
                        "anomaly_detected": vazando or atipico,
                    }


def gerar(quantidade: int) -> list[dict]:
    return list(islice(gerar_periodo(exemplo()), quantidade))
