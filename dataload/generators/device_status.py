"""Gerador da coleção device_status."""

import random
from datetime import datetime, timedelta, timezone


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
        },
        {
            "connectivity_status": "unstable",
            "wifi_signal_rssi": "weak",
            "minutes_since_ping": 15,
            "unavailability_reason": "SINAL WI-FI INSTÁVEL",
        },
        {
            "connectivity_status": "offline",
            "wifi_signal_rssi": "critical",
            "minutes_since_ping": 90,
            "unavailability_reason": "SEM CONEXÃO COM O DISPOSITIVO",
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
            }
        )

    return documentos
