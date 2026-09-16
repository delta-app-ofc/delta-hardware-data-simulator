"""Gerador de cenário de VAZAMENTO SIMULADO para consumption_summary."""

import random
from datetime import datetime, timedelta, timezone


def generate(amount: int) -> list[dict]:
    """Gera `amount` janelas consecutivas de 5 min com fluxo baixo e contínuo
    (nunca-zero), terminando de madrugada — a assinatura de um vazamento."""
    end = datetime.now(timezone.utc).replace(hour=5, minute=55, second=0, microsecond=0)
    device_id = f"ESP32-SP-{random.randint(1, 9_999):04d}"
    user_id = random.randint(1_000, 2_000_000_000)
    documents = []

    for index in range(amount):
        window_end = end - timedelta(minutes=index * 5)
        window_start = window_end - timedelta(minutes=5)
        liters = round(random.uniform(1.2, 2.2), 2)  # baixo, mas nunca 0

        documents.append(
            {
                "device_id": device_id,
                "user_id": user_id,
                "window_started_at": window_start,
                "window_finished_at": window_end,
                "consumption_liters": liters,
                "lpm_average": round(liters / 5, 2),
                "anomaly_detected": True,  # já sabemos que É vazamento simulado
            }
        )

    return documents
