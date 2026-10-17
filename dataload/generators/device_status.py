"""Status por dispositivo com contador reconciliado ao histórico de quedas."""

from datetime import timedelta
from itertools import islice

from dataload.context import aleatorio, exemplo, horario, identificador
from dataload.generators.profiles import indisponibilidades


def gerar_periodo(cenario):
    for dispositivo in cenario.dispositivos:
        inicio = horario(
            max(
                cenario.inicio,
                dispositivo["installation_date"],
                dispositivo["association_date"],
            )
        )
        fim = horario(cenario.fim)
        if inicio >= fim:
            continue
        eventos = indisponibilidades(dispositivo, cenario)
        indisponivel = sum(e["unavailable_seconds"] for e in eventos)
        sorteio = aleatorio(cenario.seed, "status", dispositivo["device_id"])
        yield {
            "_id": identificador("device_status", dispositivo["device_id"]),
            "device_id": dispositivo["device_id"],
            "last_ping_at": fim - timedelta(seconds=30),
            "wifi_signal_rssi": sorteio.choice(("excellent", "good", "weak")),
            "firmware_version": "v2.0.0-simulator",
            "connectivity_status": "online",
            "battery_level": sorteio.randint(20, 100),
            "availability_started_at": inicio,
            "availability_updated_at": fim,
            "available_seconds": int((fim - inicio).total_seconds()) - indisponivel,
            "unavailabilities": eventos,
        }


def gerar(quantidade: int) -> list[dict]:
    return list(islice(gerar_periodo(exemplo()), quantidade))
