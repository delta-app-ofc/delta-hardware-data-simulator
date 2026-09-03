"""Configuração da conexão com o MongoDB."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient


class ConfiguracaoMongoError(RuntimeError):
    """Indica que a configuração obrigatória do MongoDB está ausente."""


@lru_cache(maxsize=1)
def obter_cliente() -> MongoClient:
    """Cria um cliente reutilizável a partir da variável MONGO_URI."""
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        raise ConfiguracaoMongoError(
            "MONGO_URI não foi definida. Copie .env.example para .env e configure a conexão."
        )

    return MongoClient(mongo_uri, tz_aware=True)


def obter_colecao(nome_banco: str, nome_colecao: str):
    """Retorna uma coleção do banco configurado."""
    return obter_cliente()[nome_banco][nome_colecao]
