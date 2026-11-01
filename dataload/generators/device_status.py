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
def gerar(quantidade: int) -> list[dict]:
    """Gera um status coerente para cada dispositivo do lote."""
    documentos = []
    agora = datetime.now(timezone.utc)
    numeros_dispositivos = random.sample(range(1, 10_000), quantidade)
    cenarios = (
        {
            "connectivity_status": "online",
            "wifi_signal_rssi": "good",
            "minutes_since_ping": 2,
            "unavailability_reason": None,
            "battery_level": 88,
        },
        {
            "connectivity_status": "unstable",
            "wifi_signal_rssi": "weak",
            "minutes_since_ping": 15,
            "unavailability_reason": "SINAL WI-FI INSTÁVEL",
            "battery_level": 16,
        },
        {
            "connectivity_status": "offline",
            "wifi_signal_rssi": "critical",
            "minutes_since_ping": 90,
            "unavailability_reason": "SEM CONEXÃO COM O DISPOSITIVO",
            "battery_level": None,
        },
    )

    for indice, numero_dispositivo in enumerate(numeros_dispositivos):
        cenario = cenarios[indice % len(cenarios)]

        documentos.append(
            {
                "device_id": f"ESP32-SP-{numero_dispositivo:04d}",
                "last_ping_at": agora
                - timedelta(minutes=cenario["minutes_since_ping"]),
                "wifi_signal_rssi": cenario["wifi_signal_rssi"],
                "firmware_version": f"v1.2.{indice % 10}",
                "connectivity_status": cenario["connectivity_status"],
                "unavailability_reason": cenario["unavailability_reason"],
                "battery_level": cenario["battery_level"],
            }
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
