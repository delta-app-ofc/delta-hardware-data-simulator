import pytest

from dataload import mongo_client
from dataload.mongo_client import ConfiguracaoMongoError


@pytest.fixture(autouse=True)
def clear_client_cache():
    mongo_client.obter_cliente.cache_clear()
    yield
    mongo_client.obter_cliente.cache_clear()


def test_missing_mongo_uri_fails_before_constructing_client(monkeypatch):
    monkeypatch.setattr(mongo_client, "load_dotenv", lambda: None)
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setattr(
        mongo_client,
        "MongoClient",
        lambda *args, **kwargs: pytest.fail("cliente não deveria ser criado"),
    )

    with pytest.raises(ConfiguracaoMongoError, match="MONGO_URI"):
        mongo_client.obter_cliente()


def test_mongo_client_is_cached_and_configured_for_aware_datetimes(monkeypatch):
    calls = []
    client = object()

    def create_client(uri, **kwargs):
        calls.append((uri, kwargs))
        return client

    monkeypatch.setattr(mongo_client, "load_dotenv", lambda: None)
    monkeypatch.setenv("MONGO_URI", "mongodb://example.invalid/test")
    monkeypatch.setattr(mongo_client, "MongoClient", create_client)

    first = mongo_client.obter_cliente()
    second = mongo_client.obter_cliente()

    assert first is second is client
    assert calls == [("mongodb://example.invalid/test", {"tz_aware": True})]


def test_obter_colecao_routes_database_and_collection_names(monkeypatch):
    calls = []
    collection = object()

    class Database:
        def __getitem__(self, name):
            calls.append(("collection", name))
            return collection

    class Client:
        def __getitem__(self, name):
            calls.append(("database", name))
            return Database()

    monkeypatch.setattr(mongo_client, "obter_cliente", lambda: Client())

    result = mongo_client.obter_colecao("db_delta_app", "alerts_history")

    assert result is collection
    assert calls == [
        ("database", "db_delta_app"),
        ("collection", "alerts_history"),
    ]
