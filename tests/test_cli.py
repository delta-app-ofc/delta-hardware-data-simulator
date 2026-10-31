from types import SimpleNamespace

import pytest
from bson import json_util

from dataload import cli
from dataload.generators import chat_feedback
from dataload.mongo_client import ConfiguracaoMongoError


@pytest.mark.parametrize(
    "arguments",
    [
        ["missing", "1"],
        ["consumption_summary", "0"],
        ["consumption_summary", "101"],
        ["consumption_summary", "abc"],
        ["consumption_summary", "1", "--intervalo-segundos", "0"],
        ["consumption_summary", "1", "--tempo-maximo", "-1"],
        ["device_status", "1", "--continuo"],
    ],
)
def test_invalid_cli_arguments_fail_before_generation_or_mongo_access(arguments, monkeypatch):
    monkeypatch.setattr(
        cli, "obter_colecao", lambda *args: pytest.fail("Mongo não deveria ser acessado")
    )

    with pytest.raises(SystemExit) as caught:
        cli.executar(arguments)

    assert caught.value.code == 1


def test_noncontinuous_dry_run_serializes_documents_without_opening_mongo(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        cli,
        "obter_colecao",
        lambda *args: pytest.fail("dry-run não deve abrir conexão Mongo"),
    )

    assert cli.executar(["consumption_summary", "2", "--dry-run"]) == 0

    result = json_util.loads(capsys.readouterr().out)
    assert len(result) == 2
    assert all(item["window_finished_at"] > item["window_started_at"] for item in result)


def test_insert_many_routes_collection_and_reports_inserted_document_count(
    monkeypatch, capsys
):
    documents = [{"user_id": 1}, {"user_id": 2}]
    calls = {}

    class Collection:
        def insert_many(self, values):
            calls["documents"] = values
            return SimpleNamespace(inserted_ids=["a", "b"])

    monkeypatch.setitem(cli.GERADORES, "consumption_summary", lambda quantity: documents)
    monkeypatch.setattr(
        cli,
        "obter_colecao",
        lambda database, collection: calls.update(
            {"database": database, "collection": collection}
        )
        or Collection(),
    )

    result = cli.executar(["consumption_summary", "2"])

    assert result == 0
    assert calls == {
        "database": "db_delta_telemetry",
        "collection": "consumption_summary",
        "documents": documents,
    }
    assert "2 documento(s) inserido(s)" in capsys.readouterr().out


def test_mongo_configuration_failure_is_reported_as_cli_error(monkeypatch, capsys):
    monkeypatch.setitem(cli.GERADORES, "consumption_summary", lambda quantity: [{"x": 1}])

    def missing_configuration(*args):
        raise ConfiguracaoMongoError("MONGO_URI ausente")

    monkeypatch.setattr(cli, "obter_colecao", missing_configuration)

    assert cli.executar(["consumption_summary", "1"]) == 1
    assert "MONGO_URI ausente" in capsys.readouterr().err


def test_feedback_without_sessions_returns_error_code_without_inserting(
    monkeypatch, capsys
):
    def no_sessions(_quantity):
        raise chat_feedback.SemSessoesChatError("sem sessão de chat")

    monkeypatch.setitem(cli.GERADORES, "chat_feedback", no_sessions)
    monkeypatch.setattr(
        cli,
        "obter_colecao",
        lambda *args: pytest.fail("não deve inserir sem sessões"),
    )

    assert cli.executar(["chat_feedback", "1"]) == 1
    assert "sem sessão de chat" in capsys.readouterr().err


def test_continuous_dry_run_stops_at_requested_batch_size(monkeypatch, capsys):
    produced = []

    def generate(**kwargs):
        assert kwargs == {"intervalo_segundos": 5, "tempo_maximo": 30}
        for index in range(5):
            produced.append(index)
            yield {"sequence": index}

    monkeypatch.setattr(cli.pulses_raw, "gerar_continuo", generate)
    monkeypatch.setattr(
        cli,
        "obter_colecao",
        lambda *args: pytest.fail("dry-run contínuo não deve abrir conexão Mongo"),
    )

    assert (
        cli.executar(
            [
                "pulses_raw",
                "2",
                "--continuo",
                "--dry-run",
                "--intervalo-segundos",
                "5",
                "--tempo-maximo",
                "30",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert '"sequence": 0' in output
    assert '"sequence": 1' in output
    assert produced == [0, 1]


def test_continuous_insert_one_uses_only_requested_number_of_packets(
    monkeypatch, capsys
):
    inserted = []
    produced = []

    def generate(**kwargs):
        assert kwargs == {"intervalo_segundos": 1, "tempo_maximo": 30}
        for index in range(5):
            produced.append(index)
            yield {"sequence": index}

    class Collection:
        def insert_one(self, document):
            inserted.append(document)

    monkeypatch.setattr(cli.pulses_raw, "gerar_continuo", generate)
    monkeypatch.setattr(cli, "obter_colecao", lambda *args: Collection())

    assert (
        cli.executar(
            [
                "pulses_raw",
                "3",
                "--continuo",
                "--intervalo-segundos",
                "1",
                "--tempo-maximo",
                "30",
            ]
        )
        == 0
    )
    assert produced == [0, 1, 2]
    assert inserted == [{"sequence": 0}, {"sequence": 1}, {"sequence": 2}]
    assert "3 documento(s) inserido(s)" in capsys.readouterr().out
