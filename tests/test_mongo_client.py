"""Verifica o destino das cargas sem acessar MongoDB ou credenciais reais."""
import os
import unittest
from unittest.mock import patch

from dataload import mongo_client


class MongoClientTests(unittest.TestCase):
    def setUp(self):
        mongo_client.obter_cliente.cache_clear()
        self.addCleanup(mongo_client.obter_cliente.cache_clear)
        self.load_env = patch.object(mongo_client, "load_dotenv").start()
        self.client = patch.object(mongo_client, "MongoClient").start()
        self.addCleanup(patch.stopall)

    def test_destinos_separados_e_clientes_reutilizados(self):
        with patch.dict(os.environ, {
            "MONGO_URI_TELEMETRY": "mongodb://telemetry.example.invalid",
            "MONGO_URI_APP": "mongodb://app.example.invalid",
            "MONGO_URI": "mongodb://shared.example.invalid",
        }, clear=True):
            mongo_client.obter_colecao("db_delta_telemetry", "consumption_summary")
            mongo_client.obter_colecao("db_delta_telemetry", "device_status")
            mongo_client.obter_colecao("db_delta_app", "chat_sessions")
            mongo_client.obter_colecao("db_delta_app", "chat_feedback")
        self.assertEqual(self.client.call_count, 2)
        self.assertEqual([call.args[0] for call in self.client.call_args_list], [
            "mongodb://telemetry.example.invalid", "mongodb://app.example.invalid"])

    def test_configuracao_legada_atende_os_dois_bancos(self):
        with patch.dict(os.environ, {"MONGO_URI": "mongodb://shared.example.invalid"}, clear=True):
            mongo_client.obter_cliente("db_delta_telemetry")
            mongo_client.obter_cliente("db_delta_app")
        self.assertEqual([call.args[0] for call in self.client.call_args_list],
                         ["mongodb://shared.example.invalid"] * 2)

    def test_uri_app_nao_e_usada_para_telemetria(self):
        with patch.dict(os.environ, {"MONGO_URI_APP": "mongodb://app.example.invalid"}, clear=True):
            with self.assertRaisesRegex(mongo_client.ConfiguracaoMongoError, "MONGO_URI_TELEMETRY"):
                mongo_client.obter_cliente("db_delta_telemetry")
        self.client.assert_not_called()

    def test_uri_telemetria_nao_e_usada_para_app(self):
        with patch.dict(os.environ, {"MONGO_URI_TELEMETRY": "mongodb://telemetry.example.invalid"}, clear=True):
            with self.assertRaisesRegex(mongo_client.ConfiguracaoMongoError, "MONGO_URI_APP"):
                mongo_client.obter_cliente("db_delta_app")
        self.client.assert_not_called()

    def test_banco_desconhecido_nao_abre_conexao(self):
        with self.assertRaisesRegex(mongo_client.ConfiguracaoMongoError, "Banco não configurado"):
            mongo_client.obter_cliente("other_db")
        self.client.assert_not_called()

    def test_erro_na_uri_especifica_nao_tenta_conexao_legada(self):
        self.client.side_effect = RuntimeError("falha de conexão")
        with patch.dict(os.environ, {
            "MONGO_URI_APP": "mongodb://app.example.invalid",
            "MONGO_URI": "mongodb://shared.example.invalid",
        }, clear=True):
            with self.assertRaisesRegex(RuntimeError, "falha de conexão"):
                mongo_client.obter_cliente("db_delta_app")
        self.client.assert_called_once_with("mongodb://app.example.invalid", tz_aware=True)


if __name__ == "__main__":
    unittest.main()
