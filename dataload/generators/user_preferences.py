"""Metas dos mesmos usuários que possuem medições no cenário."""

from itertools import islice

from dataload.context import aleatorio, exemplo, identificador
from dataload.generators.profiles import base_diaria


def gerar_periodo(cenario):
    for usuario in cenario.usuarios():
        medidores = [d for d in cenario.dispositivos if d['user_id'] == usuario]
        base = sum(base_diaria(d, cenario) for d in medidores)
        sorteio = aleatorio(cenario.seed, 'meta', usuario)
        yield {'_id': identificador('user_preferences', usuario), 'user_id': usuario,
               'daily_liters_target': max(1, round(base * sorteio.uniform(0.85, 1.20))),
               'notifications_enabled': True, 'dark_mode_enabled': sorteio.choice((True, False)),
               'quiet_hours': {'start_hour': '22:00', 'end_hour': '06:00'}}


def gerar(quantidade: int) -> list[dict]:
    return list(islice(gerar_periodo(exemplo()), quantidade))
