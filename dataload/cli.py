"""Interface para prévias individuais e povoamento BI coordenado."""

import argparse
import sys
from itertools import islice

from bson import json_util

from dataload.generators import (
    alerts_history,
    chat_feedback,
    chat_sessions,
    consumption_summary,
    device_status,
    user_preferences,
    weather_daily,
)
from dataload.mongo_client import ConfiguracaoMongoError
    leak_scenario,
    pulses_raw,
    user_preferences,
    weather_daily,
)
from dataload.mongo_client import ConfiguracaoMongoError, obter_colecao


BANCOS_POR_COLECAO = {
    "pulses_raw": "db_delta_telemetry",
    "consumption_summary": "db_delta_telemetry",
    "device_status": "db_delta_telemetry",
    "user_preferences": "db_delta_app",
    "alerts_history": "db_delta_app",
    "chat_sessions": "db_delta_app",
    "chat_feedback": "db_delta_app",
    "weather_daily": "db_delta_app",
}

GERADORES = {
    "consumption_summary": consumption_summary.gerar,
    "device_status": device_status.gerar,
    "user_preferences": user_preferences.gerar,
    "alerts_history": alerts_history.gerar,
    "chat_sessions": chat_sessions.gerar,
    "chat_feedback": chat_feedback.gerar,
    "weather_daily": weather_daily.gerar,
}


class ParserDataload(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"Erro: {message}\n")


def inteiro(value: str) -> int:
    try:
        return int(value)
    except ValueError as erro:
        raise argparse.ArgumentTypeError(
            "a quantidade deve ser um número inteiro"
        ) from erro


def criar_parser() -> ParserDataload:
    parser = ParserDataload(
        description="Prévia: <coleção> <quantidade> --dry-run. Carga: bi --contexto ... --inicio ..."
    )
    parser.add_argument(
        "colecao", help="coleção atual do MongoDB; pulses_raw foi descontinuada"
    )
    parser.add_argument(
        "quantidade", type=inteiro, help="máximo entre 1 e 100 documentos"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="imprime uma prévia sem inserir no MongoDB",
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "leak"],
        default="normal",
        help=(
            "só se aplica a consumption_summary: 'normal' usa o gerador padrão, "
            "'leak' usa leak_scenario.generate (fluxo contínuo simulado, "
            "provisório até existir hardware real de vazamento)"
        ),
    )
    return parser


def validar_argumentos(
    parser: ParserDataload,
    colecao: str,
    quantidade: int,
    continuo: bool,
    intervalo_segundos: int,
    tempo_maximo: int,
    scenario: str,
) -> None:
    """Valida todas as regras antes que algum documento seja gerado."""
    if colecao not in GERADORES:
        parser.error(f"coleção inválida '{colecao}'. Opções: {', '.join(GERADORES)}")
    if not 1 <= quantidade <= 100:
        parser.error("a quantidade deve estar entre 1 e 100")


def executar(argv: list[str] | None = None) -> int:
    argumentos_cli = sys.argv[1:] if argv is None else argv
    if argumentos_cli and argumentos_cli[0] == "bi":
        from dataload.bi import executar as executar_bi
    if continuo and colecao != "pulses_raw":
        parser.error("a opção --continuo só pode ser usada com pulses_raw")

    if intervalo_segundos <= 0:
        parser.error("o intervalo deve ser maior que zero")

    if tempo_maximo <= 0:
        parser.error("o tempo máximo deve ser maior que zero")

    if scenario == "leak" and colecao != "consumption_summary":
        parser.error("--scenario leak só pode ser usado com consumption_summary")


def executar(argv: list[str] | None = None) -> int:
    parser = criar_parser()
    argumentos = parser.parse_args(argv)
    validar_argumentos(
        parser,
        argumentos.colecao,
        argumentos.quantidade,
        argumentos.continuo,
        argumentos.intervalo_segundos,
        argumentos.tempo_maximo,
        argumentos.scenario,
    )

        return executar_bi(argumentos_cli[1:])
    parser = criar_parser()
    argumentos = parser.parse_args(argumentos_cli)
    validar_argumentos(parser, argumentos.colecao, argumentos.quantidade)
    if not argumentos.dry_run:
        parser.error(
            "para inserir dados vinculados ao SQL, use 'bi --contexto ... --inicio ...'; comandos individuais são somente --dry-run"
        )
    try:
        documentos = GERADORES[argumentos.colecao](argumentos.quantidade)
        print(json_util.dumps(documentos, indent=2))
        return 0
        if argumentos.continuo:
            gerador = pulses_raw.gerar_continuo(
                intervalo_segundos=argumentos.intervalo_segundos,
                tempo_maximo=argumentos.tempo_maximo,
            )

            if argumentos.dry_run:
                for documento in islice(gerador, argumentos.quantidade):
                    print(json_util.dumps(documento, indent=2))
                return 0

            colecao = obter_colecao(
                BANCOS_POR_COLECAO[argumentos.colecao], argumentos.colecao
            )
            inseridos = 0
            for documento in islice(gerador, argumentos.quantidade):
                colecao.insert_one(documento)
                inseridos += 1

            print(
                f"{inseridos} documento(s) inserido(s) em "
                f"{BANCOS_POR_COLECAO[argumentos.colecao]}.{argumentos.colecao}."
            )
            return 0

        # --scenario leak só é válido pra consumption_summary (checado em
        # validar_argumentos); nesse caso troca o gerador padrão pelo
        # leak_scenario, mantendo o mesmo destino (BANCOS_POR_COLECAO).
        gerador = (
            leak_scenario.generate
            if argumentos.colecao == "consumption_summary" and argumentos.scenario == "leak"
            else GERADORES[argumentos.colecao]
        )
        documentos = gerador(argumentos.quantidade)

        if argumentos.dry_run:
            print(json_util.dumps(documentos, indent=2))
            return 0

        colecao = obter_colecao(
            BANCOS_POR_COLECAO[argumentos.colecao], argumentos.colecao
        )
        resultado = colecao.insert_many(documentos)
    except (ConfiguracaoMongoError, chat_feedback.SemSessoesChatError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(executar())
