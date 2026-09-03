"""Interface de linha de comando para gerar e inserir dados sintéticos."""

import argparse
import sys

from bson import json_util

from dataload.generators import (
    alerts_history,
    chat_feedback,
    chat_sessions,
    consumption_summary,
    device_status,
    pulses_raw,
    user_preferences,
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
}

GERADORES = {
    "pulses_raw": pulses_raw.gerar,
    "consumption_summary": consumption_summary.gerar,
    "device_status": device_status.gerar,
    "user_preferences": user_preferences.gerar,
    "alerts_history": alerts_history.gerar,
    "chat_sessions": chat_sessions.gerar,
    "chat_feedback": chat_feedback.gerar,
}


class ParserDataload(argparse.ArgumentParser):
    """Padroniza erros da CLI com código de saída 1."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"Erro: {message}\n")


def inteiro(value: str) -> int:
    """Converte a quantidade e produz uma mensagem amigável em caso de erro."""
    try:
        return int(value)
    except ValueError as erro:
        raise argparse.ArgumentTypeError("a quantidade deve ser um número inteiro") from erro


def criar_parser() -> ParserDataload:
    parser = ParserDataload(
        description="Gera dados sintéticos válidos para os bancos MongoDB do Projeto Delta."
    )
    parser.add_argument("colecao", help="nome da coleção que receberá os documentos")
    parser.add_argument("quantidade", type=inteiro, help="quantidade entre 1 e 100")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="imprime os documentos sem inserir no MongoDB",
    )
    return parser


def validar_argumentos(parser: ParserDataload, colecao: str, quantidade: int) -> None:
    """Valida todas as regras antes que algum documento seja gerado."""
    if colecao not in GERADORES:
        nomes_validos = ", ".join(GERADORES)
        parser.error(f"coleção inválida '{colecao}'. Opções: {nomes_validos}")

    if not 1 <= quantidade <= 100:
        parser.error("a quantidade deve estar entre 1 e 100")


def executar(argv: list[str] | None = None) -> int:
    parser = criar_parser()
    argumentos = parser.parse_args(argv)
    validar_argumentos(parser, argumentos.colecao, argumentos.quantidade)

    try:
        documentos = GERADORES[argumentos.colecao](argumentos.quantidade)

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

    print(
        f"{len(resultado.inserted_ids)} documento(s) inserido(s) em "
        f"{BANCOS_POR_COLECAO[argumentos.colecao]}.{argumentos.colecao}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(executar())
