"""Gerador da coleção alerts_history."""

import random
from datetime import datetime, timedelta, timezone


SEVERIDADES_POR_ALERTA = {
    "vazamento_continuo": ("medium", "high", None),
    "fluxo_atipico": ("low", "medium", "high", None),
    "dispositivo_offline": ("medium", "high", None),
    "leitura_impossivel": ("low", "medium", None),
}


def _gerar_resolucao(triggered_at: datetime, agora: datetime) -> datetime | None:
    if random.choice((True, False)):
        minutos_disponiveis = int((agora - triggered_at).total_seconds() // 60)
        return triggered_at + timedelta(
            minutes=random.randint(1, minutos_disponiveis)
        )
    return None


def gerar(quantidade: int) -> list[dict]:
    """Gera alertas válidos com datas coerentes e IDs BSON int32 seguros."""
    agora = datetime.now(timezone.utc)
    documentos = []

    for _ in range(quantidade):
        alert_type = random.choice(tuple(SEVERIDADES_POR_ALERTA))
        triggered_at = agora - timedelta(minutes=random.randint(60, 43_200))

        documentos.append(
            {
                "device_id": f"ESP32-SP-{random.randint(1, 9_999):04d}",
                "user_id": random.randint(1_000, 2_000_000_000),
                "alert_type": alert_type,
                "triggered_at": triggered_at,
                "resolved_at": _gerar_resolucao(triggered_at, agora),
                "severity": random.choice(SEVERIDADES_POR_ALERTA[alert_type]),
            }
        )

    return documentos
