"""Gerador de cenário de VAZAMENTO SIMULADO para consumption_summary.

Provisório: até o hardware real (contratado) enviar dados de vazamento de
verdade, este gerador serve pra validar as regras/modelo de detecção do
delta-artificial-intelligence (pasta `detection/` daquele repositório). Ao
contrário de `consumption_summary.gerar()`, aqui o consumo NUNCA cai a ~zero
durante a janela simulada — essa é a assinatura que diferencia um vazamento de
um uso normal (que é sempre em rajadas curtas, intercaladas com consumo zero).

Nomenclatura: o nome desta função (`generate`) está em inglês, diferente do
`gerar()` já usado pelos outros geradores deste módulo — decisão da tarefa que
criou este arquivo (identificadores de código em inglês, comentários em
português). Isso gera uma pequena inconsistência com o restante deste
repositório, que fica registrada aqui de propósito; renomear os geradores já
existentes é uma decisão maior, à parte, que cabe ao time do
delta-hardware-data-simulator.
"""

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
