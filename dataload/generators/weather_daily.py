"""Gerador de observações meteorológicas diárias."""

import random
from datetime import datetime, timedelta, timezone


CONDICOES = ("Clear", "Clouds", "Rain")


def gerar(quantidade: int) -> list[dict]:
    """Gera um documento por dia, com 24 observações horárias ordenadas."""
    hoje = datetime.now(timezone.utc).date()
    documentos = []

    for indice in range(quantidade):
        dia = hoje - timedelta(days=indice + 1)
        inicio_do_dia = datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)
        horas = []

        for hora in range(24):
            observado_em = inicio_do_dia + timedelta(hours=hora)
            temperatura = round(random.uniform(12.0, 32.0), 1)
            vento = round(random.uniform(0.0, 8.0), 1)

            horas.append(
                {
                    "hour": hora,
                    "observed_at": observado_em,
                    "temperature_c": temperatura,
                    "feels_like_c": round(temperatura + random.uniform(-2, 2), 1),
                    "humidity_percent": random.randint(25, 100),
                    "pressure_hpa": round(random.uniform(990.0, 1035.0), 1),
                    "rain_mm": round(random.uniform(0.0, 8.0), 1),
                    "cloud_coverage_percent": random.randint(0, 100),
                    "wind_speed_m_s": vento,
                    "wind_gust_m_s": round(vento + random.uniform(0, 5), 1),
                    "condition": random.choice(CONDICOES),
                }
            )

        documentos.append(
            {
                "location": {
                    "city": "São Paulo",
                    "state": "SP",
                    "country": "BR",
                },
                "date": inicio_do_dia,
                "hours": horas,
                "samples": len(horas),
                "created_at": inicio_do_dia + timedelta(minutes=1),
                "updated_at": inicio_do_dia + timedelta(hours=23, minutes=1),
            }
        )

    return documentos
