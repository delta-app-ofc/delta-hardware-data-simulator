"""Interface para prévias individuais e povoamento BI coordenado."""

import argparse
import sys

from bson import json_util

from dataload.generators import (
    alerts_history, chat_feedback, chat_sessions, consumption_summary,
    device_status, user_preferences, weather_daily,
)
from dataload.mongo_client import ConfiguracaoMongoError

GERADORES = {
    'consumption_summary': consumption_summary.gerar,
    'device_status': device_status.gerar,
    'user_preferences': user_preferences.gerar,
    'alerts_history': alerts_history.gerar,
    'chat_sessions': chat_sessions.gerar,
    'chat_feedback': chat_feedback.gerar,
    'weather_daily': weather_daily.gerar,
}


class ParserDataload(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f'Erro: {message}\n')


def inteiro(value: str) -> int:
    try:
        return int(value)
    except ValueError as erro:
        raise argparse.ArgumentTypeError('a quantidade deve ser um número inteiro') from erro


def criar_parser() -> ParserDataload:
    parser = ParserDataload(description='Prévia: <coleção> <quantidade> --dry-run. Carga: bi --contexto ... --inicio ...')
    parser.add_argument('colecao', help='coleção atual do MongoDB; pulses_raw foi descontinuada')
    parser.add_argument('quantidade', type=inteiro, help='máximo entre 1 e 100 documentos')
    parser.add_argument('--dry-run', action='store_true', help='imprime uma prévia sem inserir no MongoDB')
    return parser


def validar_argumentos(parser, colecao, quantidade):
    if colecao not in GERADORES:
        parser.error(f"coleção inválida '{colecao}'. Opções: {', '.join(GERADORES)}")
    if not 1 <= quantidade <= 100:
        parser.error('a quantidade deve estar entre 1 e 100')


def executar(argv: list[str] | None = None) -> int:
    argumentos_cli = sys.argv[1:] if argv is None else argv
    if argumentos_cli and argumentos_cli[0] == 'bi':
        from dataload.bi import executar as executar_bi
        return executar_bi(argumentos_cli[1:])
    parser = criar_parser()
    argumentos = parser.parse_args(argumentos_cli)
    validar_argumentos(parser, argumentos.colecao, argumentos.quantidade)
    if not argumentos.dry_run:
        parser.error("para inserir dados vinculados ao SQL, use 'bi --contexto ... --inicio ...'; comandos individuais são somente --dry-run")
    try:
        documentos = GERADORES[argumentos.colecao](argumentos.quantidade)
        print(json_util.dumps(documentos, indent=2))
        return 0
    except (ConfiguracaoMongoError, chat_feedback.SemSessoesChatError) as erro:
        print(f'Erro: {erro}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(executar())
