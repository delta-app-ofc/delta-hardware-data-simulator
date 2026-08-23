"""Simulador dos pacotes de pulsos enviados pelo ESP32."""

import random
from datetime import datetime, timedelta, timezone


JANELA_MINUTOS = 5
JANELA_MILISSEGUNDOS = JANELA_MINUTOS * 60 * 1_000


def gerar(quantidade: int) -> list[dict]:
    """Gera pacotes sucessivos de um dispositivo com uptime crescente."""
    agora = datetime.now(timezone.utc).replace(microsecond=0)
    inicio_simulacao = agora - timedelta(minutes=quantidade * JANELA_MINUTOS)
    device_id = f"ESP32-SP-{random.randint(1, 9_999):04d}"
    uptime_inicial_ms = random.randint(1_800_000, 86_400_000)
    documentos = []

    for indice in range(quantidade):
        sent_at = inicio_simulacao + timedelta(
            minutes=(indice + 1) * JANELA_MINUTOS
        )
        total_pulses = random.randint(1, 8)

        # Os deslocamentos ordenados mantêm pulsos, deltas e uptime coerentes.
        deslocamentos_ms = sorted(
            random.sample(range(1_000, JANELA_MILISSEGUNDOS), total_pulses)
        )
        pulses = []
        deslocamento_anterior = None

        for deslocamento_ms in deslocamentos_ms:
            delta_ms = (
                0
                if deslocamento_anterior is None
                else deslocamento_ms - deslocamento_anterior
            )
            pulses.append(
                {
                    "pulsed_at": sent_at
                    - timedelta(minutes=JANELA_MINUTOS)
                    + timedelta(milliseconds=deslocamento_ms),
                    "ms_since_boot": uptime_inicial_ms
                    + indice * JANELA_MILISSEGUNDOS
                    + deslocamento_ms,
                    "delta_ms": delta_ms,
                }
            )
            deslocamento_anterior = deslocamento_ms

        documentos.append(
            {
                "device_id": device_id,
                "sent_at": sent_at,
                "window_minutes": JANELA_MINUTOS,
                "total_pulses": total_pulses,
                "pulses": pulses,
            }
        )

    return documentos
