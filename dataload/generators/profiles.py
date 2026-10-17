"""Regras simples compartilhadas por consumo, alertas, metas e disponibilidade."""

from datetime import timedelta

from dataload.context import aleatorio, horario


def base_diaria(dispositivo, cenario):
    residencial = dispositivo["classification_group"] == "RESIDENCIAL"
    sorteio = aleatorio(cenario.seed, "imovel", dispositivo["property_id"])
    base = sorteio.uniform(240, 460) if residencial else sorteio.uniform(900, 1800)
    medidores = sum(d["property_id"] == dispositivo["property_id"] for d in cenario.dispositivos)
    return base / medidores


def eventos_do_dia(dispositivo, dia, seed):
    sorteio = aleatorio(seed, "eventos", dispositivo["device_id"], dia)
    return {"vazamento_continuo": sorteio.random() < 0.10,
            "fluxo_atipico": sorteio.random() < 0.18,
            "dispositivo_offline": sorteio.random() < 0.25,
            "leitura_impossivel": sorteio.random() < 0.08}


def indisponibilidades(dispositivo, cenario):
    eventos = []
    for dia in cenario.dias():
        if cenario.ativo(dispositivo, dia) and eventos_do_dia(dispositivo, dia, cenario.seed)["dispositivo_offline"]:
            minutos = aleatorio(cenario.seed, "offline", dispositivo["device_id"], dia).randint(5, 100)
            inicio = horario(dia, 22)
            eventos.append({"started_at": inicio, "ended_at": inicio + timedelta(minutes=minutos),
                            "unavailable_seconds": minutos * 60,
                            "unavailability_reason": "OSCILACAO DE ENERGIA" if minutos > 45 else "REDE WI-FI INDISPONIVEL"})
    return eventos
