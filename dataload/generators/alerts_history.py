"""Alertas coerentes com os eventos simulados de cada dispositivo/dia."""

from datetime import timedelta
from itertools import islice

from dataload.context import aleatorio, exemplo, horario, identificador
from dataload.generators.profiles import eventos_do_dia


def gerar_periodo(cenario):
    horas = {'vazamento_continuo': 4, 'fluxo_atipico': 10, 'dispositivo_offline': 22, 'leitura_impossivel': 15}
    for dia in cenario.dias():
        for dispositivo in cenario.dispositivos:
            if not cenario.ativo(dispositivo, dia):
                continue
            for tipo, ocorre in eventos_do_dia(dispositivo, dia, cenario.seed).items():
                if not ocorre:
                    continue
                instante = horario(dia, horas[tipo])
                minutos = {'vazamento_continuo': 120, 'fluxo_atipico': 60, 'leitura_impossivel': 30}.get(tipo)
                if tipo == 'dispositivo_offline':
                    minutos = aleatorio(cenario.seed, 'offline', dispositivo['device_id'], dia).randint(5, 100)
                yield {'_id': identificador('alerts_history', dispositivo['device_id'], dia, tipo),
                       'device_id': dispositivo['device_id'], 'user_id': dispositivo['user_id'],
                       'alert_type': tipo, 'triggered_at': instante,
                       'resolved_at': instante + timedelta(minutes=minutos),
                       'severity': 'high' if tipo == 'vazamento_continuo' else 'medium' if tipo == 'dispositivo_offline' else 'low'}


def gerar(quantidade: int) -> list[dict]:
    return list(islice(gerar_periodo(exemplo()), quantidade))
