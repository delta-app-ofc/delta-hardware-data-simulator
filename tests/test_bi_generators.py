"""Verifica contratos BSON e relações do cenário, sem acessar bancos."""

import json
import math
import tempfile
import unittest
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from bson import BSON, ObjectId

from dataload.bi import COLECOES
from dataload.context import EXEMPLO, Cenario, carregar_contexto

SCHEMAS = json.loads(
    (Path(__file__).parent / "fixtures/mongo-schemas.json").read_text(encoding="utf-8")
)["collections"]


def validar_bson(valor, schema, caminho="documento"):
    """Subconjunto dos validators reais usado por estas sete coleções."""
    tipos = schema.get("bsonType", [])
    tipos = [tipos] if isinstance(tipos, str) else tipos
    testes = {
        "object": isinstance(valor, dict),
        "array": isinstance(valor, list),
        "objectId": isinstance(valor, ObjectId),
        "date": isinstance(valor, datetime),
        "string": isinstance(valor, str),
        "bool": type(valor) is bool,
        "int": type(valor) is int and -(2**31) <= valor < 2**31,
        "long": type(valor) is int and -(2**63) <= valor < 2**63,
        "double": type(valor) is float and math.isfinite(valor),
        "null": valor is None,
    }
    assert not tipos or any(testes.get(tipo, False) for tipo in tipos), (
        caminho,
        tipos,
        valor,
    )
    if "enum" in schema:
        assert valor in schema["enum"], (caminho, valor)
    for limite, operador in (
        ("minimum", lambda a, b: a >= b),
        ("maximum", lambda a, b: a <= b),
    ):
        if limite in schema and valor is not None:
            assert operador(valor, schema[limite]), caminho
    if isinstance(valor, str):
        assert len(valor) >= schema.get("minLength", 0), caminho
    if isinstance(valor, dict):
        propriedades = schema.get("properties", {})
        assert set(schema.get("required", [])) <= valor.keys(), caminho
        assert valor.keys() <= propriedades.keys(), (
            caminho,
            "campo não declarado",
            valor.keys() - propriedades.keys(),
        )
        for chave, dependencias in schema.get("dependencies", {}).items():
            if chave in valor:
                assert set(dependencias) <= valor.keys(), caminho
        for chave, item in valor.items():
            validar_bson(item, propriedades[chave], caminho + "." + chave)
    if isinstance(valor, list):
        assert len(valor) <= schema.get("maxItems", float("inf")), caminho
        for indice, item in enumerate(valor):
            validar_bson(item, schema["items"], caminho + f"[{indice}]")


class GeneratorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contexto = carregar_contexto(EXEMPLO)
        cls.cenario = Cenario(cls.contexto, date(2026, 9, 1), date(2026, 10, 1))
        cls.documentos = {
            nome: list(modulo.gerar_periodo(cls.cenario))
            for nome, (_, modulo) in COLECOES.items()
        }

    def test_todos_os_documentos_respeitam_validators_e_campos_declarados(self):
        for nome, documentos in self.documentos.items():
            banco, _ = COLECOES[nome]
            self.assertTrue(documentos, nome)
            for documento in documentos:
                BSON.encode(documento)
                validar_bson(documento, SCHEMAS[f"{banco}.{nome}"], nome)

    def test_mesmos_dispositivos_usuarios_e_ids_unicos_em_todas_as_colecoes(self):
        vinculos = {d["device_id"]: d["user_id"] for d in self.contexto}
        usuarios = set(vinculos.values())
        for nome, documentos in self.documentos.items():
            self.assertEqual(len(documentos), len({d["_id"] for d in documentos}), nome)
            for doc in documentos:
                if "device_id" in doc:
                    self.assertIn(doc["device_id"], vinculos)
                    if "user_id" in doc:
                        self.assertEqual(doc["user_id"], vinculos[doc["device_id"]])
                elif "user_id" in doc:
                    self.assertIn(doc["user_id"], usuarios)

    def test_clima_tem_24_horas_e_cidades_sem_variantes_de_grafia(self):
        self.assertEqual(len(self.documentos["weather_daily"]), 30 * 3)
        for doc in self.documentos["weather_daily"]:
            self.assertEqual(doc["samples"], 24)
            self.assertEqual([h["hour"] for h in doc["hours"]], list(range(24)))
            self.assertEqual(doc["hours"][0]["observed_at"], doc["weather_date"])
            self.assertTrue(all(h["feels_like_c"] is not None for h in doc["hours"]))
        faixas = {
            int(h["temperature_c"] // 5)
            for d in self.documentos["weather_daily"]
            for h in d["hours"]
        }
        self.assertGreaterEqual(len(faixas), 5)

    def test_consumo_tem_todas_as_horas_pareadas_ao_clima_e_dias_completos(self):
        cidades = {d["device_id"]: d["city"] for d in self.contexto}
        horas_clima = {
            (d["location"]["city"], h["observed_at"])
            for d in self.documentos["weather_daily"]
            for h in d["hours"]
        }
        contagem = Counter()
        diario = defaultdict(float)
        for doc in self.documentos["consumption_summary"]:
            inicio = doc["window_started_at"]
            self.assertEqual((doc["window_finished_at"] - inicio).total_seconds(), 300)
            self.assertIn(
                (cidades[doc["device_id"]], inicio.replace(minute=0)), horas_clima
            )
            self.assertGreaterEqual(doc["consumption_liters"], 0)
            self.assertAlmostEqual(
                doc["lpm_average"] * 5, doc["consumption_liters"], places=4
            )
            contagem[doc["device_id"], inicio.replace(minute=0)] += 1
            diario[doc["device_id"]] += doc["consumption_liters"]
        self.assertEqual(set(contagem.values()), {12})
        self.assertEqual(len(contagem), 4 * 30 * 24)
        residencial = sum(
            diario[d["device_id"]]
            for d in self.contexto
            if d["classification_group"] == "RESIDENCIAL"
        )
        comercial = sum(
            diario[d["device_id"]]
            for d in self.contexto
            if d["classification_group"] == "COMERCIAL"
        )
        self.assertGreater(comercial, residencial)

    def test_alertas_offline_coincidem_com_intervalos_e_contadores(self):
        alertas = {
            (d["device_id"], d["triggered_at"]): d
            for d in self.documentos["alerts_history"]
            if d["alert_type"] == "dispositivo_offline"
        }
        self.assertEqual(
            {d["alert_type"] for d in self.documentos["alerts_history"]},
            {
                "vazamento_continuo",
                "fluxo_atipico",
                "dispositivo_offline",
                "leitura_impossivel",
            },
        )
        percentuais = set()
        for status in self.documentos["device_status"]:
            esperado = (
                status["availability_updated_at"] - status["availability_started_at"]
            ).total_seconds()
            segundos = 0
            for evento in status["unavailabilities"]:
                self.assertEqual(
                    evento["unavailable_seconds"],
                    (evento["ended_at"] - evento["started_at"]).total_seconds(),
                )
                self.assertEqual(
                    alertas[status["device_id"], evento["started_at"]]["resolved_at"],
                    evento["ended_at"],
                )
                segundos += evento["unavailable_seconds"]
            self.assertEqual(status["available_seconds"] + segundos, esperado)
            percentuais.add(round(100 * status["available_seconds"] / esperado, 3))
        self.assertGreater(len(percentuais), 1)

    def test_chat_tem_falhas_temporais_amostras_individuais_e_feedbacks_reais_do_cenario(
        self,
    ):
        agentes, erros, duracoes = set(), set(), set()
        ids = {s["_id"] for s in self.documentos["chat_sessions"]}
        for sessao in self.documentos["chat_sessions"]:
            self.assertEqual(len(sessao["messages"]), 6)
            for mensagem in sessao["messages"]:
                if mensagem["role"] == "bot":
                    agentes.add(mensagem["agent_name"])
                    duracoes.add(mensagem["response_time_ms"])
                    if mensagem["api_status_code"] >= 400:
                        erros.add(mensagem["sent_at"].date())
        self.assertEqual(agentes, {"leak", "forecast", "consumption"})
        self.assertGreater(len(duracoes), 100)
        self.assertGreater(len(erros), 10)
        self.assertTrue(
            all(f["session_id"] in ids for f in self.documentos["chat_feedback"])
        )

    def test_meta_diaria_produz_dias_dentro_e_fora_da_meta(self):
        metas = {
            d["user_id"]: d["daily_liters_target"]
            for d in self.documentos["user_preferences"]
        }
        dias = defaultdict(float)
        for doc in self.documentos["consumption_summary"]:
            dias[
                doc["user_id"], (doc["window_started_at"] - timedelta(hours=3)).date()
            ] += doc["consumption_liters"]
        self.assertEqual(
            {litros <= metas[usuario] for (usuario, _), litros in dias.items()},
            {True, False},
        )

    def test_repetir_ou_ampliar_periodo_nao_muda_observacoes_anteriores(self):
        curto = Cenario(self.contexto, date(2026, 9, 1), date(2026, 9, 3))
        maior = Cenario(self.contexto, date(2026, 9, 1), date(2026, 9, 4))
        for nome, (_, modulo) in COLECOES.items():
            a = list(modulo.gerar_periodo(curto))
            b = {d["_id"]: d for d in modulo.gerar_periodo(maior)}
            for doc in a:
                if nome != "device_status":
                    self.assertEqual(doc, b[doc["_id"]], nome)

    def test_contexto_rejeita_ids_coordenadas_e_grafias_inconsistentes(self):
        original = json.loads(EXEMPLO.read_text(encoding="utf-8"))
        for campo, valor in (
            ("latitude", None),
            ("user_id", True),
            ("state", "RJ"),
            ("device_id", " ESP32 "),
        ):
            with self.subTest(campo=campo), tempfile.TemporaryDirectory() as temp:
                dados = json.loads(json.dumps(original))
                dados["devices"][0][campo] = valor
                path = Path(temp) / "contexto.json"
                path.write_text(json.dumps(dados), encoding="utf-8")
                with self.assertRaises(ValueError):
                    carregar_contexto(path)

    def test_coordenadas_ausentes_exigem_opcao_e_nao_sao_inventadas(self):
        dados = json.loads(EXEMPLO.read_text(encoding="utf-8"))
        dados["devices"][0]["latitude"] = None
        dados["devices"][0]["longitude"] = None
        dados["devices"][0]["city"] = "Sao Paulo"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contexto.json"
            path.write_text(json.dumps(dados), encoding="utf-8")
            with self.assertRaises(ValueError):
                carregar_contexto(path)
            contexto = carregar_contexto(path, permitir_coordenadas_ausentes=True)
            self.assertIsNone(contexto[0]["latitude"])
            self.assertIsNone(contexto[0]["longitude"])
            self.assertEqual(contexto[0]["city"], "SAO PAULO")
            self.assertEqual(contexto[1]["city"], "SAO PAULO")
            cenario = Cenario(contexto, date(2026, 9, 1), date(2026, 9, 2))
            modulo = COLECOES["weather_daily"][1]
            clima = list(modulo.gerar_periodo(cenario))
            self.assertEqual(len(clima), 3)
            self.assertTrue(all(len(d["hours"]) == 24 for d in clima))
            self.assertTrue(
                all("latitude" not in d and "longitude" not in d for d in clima)
            )


if __name__ == "__main__":
    unittest.main()
