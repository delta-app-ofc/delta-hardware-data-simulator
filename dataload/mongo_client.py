"""Configuração da conexão com o MongoDB."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient


class ConfiguracaoMongoError(RuntimeError):
    """Indica que a configuração obrigatória do MongoDB está ausente."""


VARIAVEIS_POR_BANCO = {
    "db_delta_telemetry": "MONGO_URI_TELEMETRY",
    "db_delta_app": "MONGO_URI_APP",
}


@lru_cache(maxsize=2)
def obter_cliente(nome_banco: str) -> MongoClient:
    """Reutiliza uma conexão por banco, permitindo clusters separados."""
    if nome_banco not in VARIAVEIS_POR_BANCO:
        raise ConfiguracaoMongoError(f"Banco não configurado: {nome_banco}.")
    load_dotenv()
    variavel = VARIAVEIS_POR_BANCO[nome_banco]
    mongo_uri = os.getenv(variavel) or os.getenv("MONGO_URI")

    if not mongo_uri:
        raise ConfiguracaoMongoError(
            f"{variavel} não foi definida para {nome_banco}. "
            "Configure a URI específica ou MONGO_URI para uma instância compartilhada."
        )

    return MongoClient(mongo_uri, tz_aware=True)


def obter_colecao(nome_banco: str, nome_colecao: str):
    """Retorna uma coleção do banco configurado."""
    return obter_cliente(nome_banco)[nome_banco][nome_colecao]
