"""Gerador da coleção consumption_summary."""

from datetime import datetime, timedelta, timezone


def gerar(quantidade: int) -> list[dict]:
    """Gera resumos de consumo em janelas consecutivas de cinco minutos."""
    documentos = []
    fim_mais_recente = datetime.now(timezone.utc)

    for indice in range(quantidade):
        fim_da_janela = fim_mais_recente - timedelta(minutes=indice * 5)
        inicio_da_janela = fim_da_janela - timedelta(minutes=5)

        # A variação determinística facilita conferir os dados no dry-run.
        consumo_litros = round(2.5 + (indice % 20) * 0.75, 2)
        vazao_media = round(consumo_litros / 5, 2)

        documentos.append(
            {
                "device_id": f"ESP32-SP-{1000 + indice:04d}",
                "user_id": 200 + indice,
                "window_started_at": inicio_da_janela,
                "window_finished_at": fim_da_janela,
                "consumption_liters": float(consumo_litros),
                "lpm_average": float(vazao_media),
                "anomaly_detected": consumo_litros >= 15.0,
            }
        )

    return documentos
