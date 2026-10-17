"""Testa idempotência e preflight com destino em memória; não é integração Mongo."""

import contextlib
import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from bson import ObjectId, json_util
from test_bi_generators import SCHEMAS

from dataload import bi, cli
from dataload.context import EXEMPLO


def campo(documento, nome):
    for parte in nome.split("."):
        documento = documento.get(parte) if isinstance(documento, dict) else None
    return documento


def corresponde(documento, consulta):
    for chave, esperado in consulta.items():
        valor = campo(documento, chave)
        if isinstance(esperado, dict):
            for operador, limite in esperado.items():
                if (
                    valor is None
                    or (operador == "$lt" and not valor < limite)
                    or (operador == "$gt" and not valor > limite)
                    or (operador == "$gte" and not valor >= limite)
                ):
                    return False
        elif valor != esperado:
            return False
    return True


class ColecaoMemoria:
    def __init__(self, nome):
        self.nome, self.documentos, self.escritas = nome, {}, 0
        self.database = self

    def list_collections(self, filter):
        banco = bi.COLECOES[self.nome][0]
        return iter(
            [
                {
                    "options": {
                        "validator": {"$jsonSchema": SCHEMAS[f"{banco}.{self.nome}"]}
                    }
                }
            ]
        )

    def list_indexes(self):
        return [
            {
                "unique": True,
                "key": {
                    "location.city": 1,
                    "location.state": 1,
                    "location.country": 1,
                    "weather_date": -1,
                },
            }
        ]

    def find(self, consulta, projection=None):
        return (d for d in self.documentos.values() if corresponde(d, consulta))

    def find_one(self, consulta):
        return next(self.find(consulta), None)

    def bulk_write(self, operacoes, ordered):
        for operacao in operacoes:
            self.escritas += 1
            filtro, documento = operacao._filter, operacao._doc.copy()
            chave = json_util.dumps(filtro, sort_keys=True)
            anterior = self.documentos.get(chave, {})
            documento.setdefault("_id", anterior.get("_id", ObjectId()))
            self.documentos[chave] = documento


class LoadTests(unittest.TestCase):
    def setUp(self):
        self.colecoes = {nome: ColecaoMemoria(nome) for nome in bi.COLECOES}
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.contexto = Path(self.temp.name) / "sql.json"
        self.contexto.write_bytes(EXEMPLO.read_bytes())

    def executar(self, fim="2026-09-03", extras=()):
        with (
            patch.object(
                bi, "obter_colecao", side_effect=lambda banco, nome: self.colecoes[nome]
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            return bi.executar(
                [
                    "--contexto",
                    str(self.contexto),
                    "--inicio",
                    "2026-09-01",
                    "--fim",
                    fim,
                    "--max-documentos",
                    "10000",
                    *extras,
                ]
            )

    def test_repeticao_nao_duplica_e_ampliacao_acrescenta_dias(self):
        self.assertEqual(self.executar(), 0)
        contagens = {n: len(c.documentos) for n, c in self.colecoes.items()}
        self.assertEqual(contagens["consumption_summary"], 4 * 2 * 288)
        ids = {
            n: {d["_id"] for d in c.documentos.values()}
            for n, c in self.colecoes.items()
        }
        self.assertEqual(self.executar(), 0)
        self.assertEqual(
            contagens, {n: len(c.documentos) for n, c in self.colecoes.items()}
        )
        self.assertTrue(
            all(
                ids[n] == {d["_id"] for d in c.documentos.values()}
                for n, c in self.colecoes.items()
            )
        )
        self.assertEqual(self.executar(fim="2026-09-04"), 0)
        self.assertEqual(
            len(self.colecoes["consumption_summary"].documentos), 4 * 3 * 288
        )
        self.assertEqual(len(self.colecoes["device_status"].documentos), 4)
        sessoes = {s["_id"] for s in self.colecoes["chat_sessions"].documentos.values()}
        self.assertTrue(
            all(
                f["session_id"] in sessoes
                for f in self.colecoes["chat_feedback"].documentos.values()
            )
        )

    def test_dry_run_nao_abre_conexao(self):
        with patch.object(bi, "obter_colecao") as conexao:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    bi.executar(
                        [
                            "--contexto",
                            str(EXEMPLO),
                            "--inicio",
                            "2026-09-01",
                            "--fim",
                            "2026-09-02",
                            "--dry-run",
                        ]
                    ),
                    0,
                )
            conexao.assert_not_called()

    def test_limite_total_falha_antes_de_conectar_ou_gravar(self):
        with patch.object(bi, "obter_colecao") as conexao:
            self.assertEqual(self.executar(extras=("--max-documentos", "100")), 1)
            conexao.assert_not_called()
        self.assertEqual(sum(c.escritas for c in self.colecoes.values()), 0)

    def test_modo_horario_cabe_no_teto_de_2000_e_nao_mistura_grades(self):
        extras = ("--janela-minutos", "60", "--max-documentos", "2000")
        self.assertEqual(self.executar(extras=extras), 0)
        self.assertEqual(len(self.colecoes["consumption_summary"].documentos), 192)
        escritas = sum(c.escritas for c in self.colecoes.values())
        self.assertEqual(self.executar(), 1)
        self.assertEqual(escritas, sum(c.escritas for c in self.colecoes.values()))

    def test_limite_contabiliza_todas_as_colecoes_sem_truncar(self):
        # Só o consumo caberia; clima, alertas, sessões e demais saídas também contam.
        with patch.object(bi, "obter_colecao") as conexao:
            self.assertEqual(self.executar(extras=("--max-documentos", "2310")), 1)
            conexao.assert_not_called()
        self.assertEqual(sum(c.escritas for c in self.colecoes.values()), 0)

    def test_exemplo_ficticio_nao_pode_ser_inserido(self):
        with (
            patch.object(bi, "obter_colecao") as conexao,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(
                bi.executar(
                    [
                        "--contexto",
                        str(EXEMPLO),
                        "--inicio",
                        "2026-09-01",
                        "--fim",
                        "2026-09-02",
                    ]
                ),
                1,
            )
            conexao.assert_not_called()

    def test_historico_maior_nao_e_truncado(self):
        self.assertEqual(self.executar(fim="2026-09-04"), 0)
        escritas = sum(c.escritas for c in self.colecoes.values())
        self.assertEqual(self.executar(fim="2026-09-03"), 1)
        self.assertEqual(escritas, sum(c.escritas for c in self.colecoes.values()))

    def test_indice_legado_impede_carga_mesmo_com_indice_novo_presente(self):
        clima = self.colecoes["weather_daily"]
        indices = clima.list_indexes() + [
            {"unique": True, "key": {"location.city": 1, "date": -1}}
        ]
        with patch.object(clima, "list_indexes", return_value=indices):
            self.assertEqual(self.executar(), 1)
        self.assertEqual(sum(c.escritas for c in self.colecoes.values()), 0)

    def test_clima_com_grafia_legada_falha_antes_da_primeira_escrita(self):
        self.colecoes["weather_daily"].documentos["legado"] = {
            "location": {"city": "Sao Paulo", "state": "SP", "country": "BR"},
            "weather_date": datetime(2026, 9, 1, tzinfo=timezone.utc),
        }
        self.assertEqual(self.executar(), 1)
        self.assertEqual(sum(c.escritas for c in self.colecoes.values()), 0)

    def test_cli_rejeita_quantidade_invalida_e_colecao_legada_sem_gerar(self):
        for argumentos in (
            ("weather_daily", "0", "--dry-run"),
            ("weather_daily", "101", "--dry-run"),
            ("pulses_raw", "1", "--dry-run"),
        ):
            with (
                self.subTest(argumentos=argumentos),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                cli.executar(list(argumentos))


if __name__ == "__main__":
    unittest.main()
