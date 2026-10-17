"""Povoamento coordenado das sete coleções atuais para os dashboards BI."""

import argparse
from datetime import date, datetime, timedelta, timezone
from itertools import islice
import sys

from bson import json_util
from pymongo import ReplaceOne

from dataload.context import Cenario, EXEMPLO, FUSO, carregar_contexto, chave_cidade, horario
from dataload.generators import (
    alerts_history, chat_feedback, chat_sessions, consumption_summary,
    device_status, user_preferences, weather_daily,
)
from dataload.mongo_client import ConfiguracaoMongoError, obter_colecao

COLECOES = {
    "weather_daily": ("db_delta_app", weather_daily),
    "consumption_summary": ("db_delta_telemetry", consumption_summary),
    "device_status": ("db_delta_telemetry", device_status),
    "user_preferences": ("db_delta_app", user_preferences),
    "alerts_history": ("db_delta_app", alerts_history),
    "chat_sessions": ("db_delta_app", chat_sessions),
    "chat_feedback": ("db_delta_app", chat_feedback),
}


def filtro_documento(nome, documento):
    """Usa as chaves reais; repetições substituem a observação, sem duplicar janelas."""
    campos = {
        "weather_daily": ("location", "weather_date"),
        "consumption_summary": ("device_id", "window_started_at", "window_finished_at"),
        "device_status": ("device_id",), "user_preferences": ("user_id",),
    }.get(nome, ("_id",))
    if nome == "weather_daily":
        return {"location.city": documento["location"]["city"], "location.state": "SP",
                "location.country": "BR", "weather_date": documento["weather_date"]}
    return {campo: documento[campo] for campo in campos}


def preflight(cenario, colecoes):
    """Confere destino e dados anteriores antes da primeira escrita do cenário."""
    for nome, colecao in colecoes.items():
        definicao = next(colecao.database.list_collections(filter={"name": nome}), None)
        if not definicao or "$jsonSchema" not in definicao.get("options", {}).get("validator", {}):
            raise ValueError(f"{nome}: coleção/validator ausente. Aplique o contrato do delta-mongo-database antes da carga.")
        schema = definicao["options"]["validator"]["$jsonSchema"]["properties"]
        if nome == "chat_sessions":
            campos = schema["messages"]["items"]["properties"]
            if not {"agent_name", "response_time_ms"} <= campos.keys():
                raise ValueError("Atualize o validator de chat_sessions: faltam campos de latência.")
        if nome == "device_status" and not {"available_seconds", "unavailabilities"} <= schema.keys():
            raise ValueError("Atualize o validator de device_status: falta o histórico de disponibilidade.")
    indices = list(colecoes["weather_daily"].list_indexes())
    if not any(i.get("unique") and set(i["key"]) == {"location.country", "location.state", "location.city", "weather_date"} for i in indices):
        raise ValueError("weather_daily precisa do índice único atual por localização/weather_date; não use o índice legado date.")
    for documento in device_status.gerar_periodo(cenario):
        anterior = colecoes["device_status"].find_one({"device_id": documento["device_id"]})
        if anterior and ((anterior.get("availability_started_at") or documento["availability_started_at"]) < documento["availability_started_at"]
                         or (anterior.get("availability_updated_at") or documento["availability_updated_at"]) > documento["availability_updated_at"]):
            raise ValueError("O status já cobre período maior. Amplie --inicio/--fim para preservar seu histórico.")
    for local in cenario.locais():
        # Registros legados podem usar meia-noite UTC em vez da meia-noite local.
        inicio_utc = datetime.combine(cenario.inicio, datetime.min.time(), timezone.utc)
        consulta = {"weather_date": {"$gte": inicio_utc, "$lt": horario(cenario.fim)}}
        for anterior in colecoes["weather_daily"].find(consulta, {"location": 1, "weather_date": 1}):
            cidade = anterior.get("location", {}).get("city", "")
            if chave_cidade(cidade) == chave_cidade(local["city"]):
                if cidade != local["city"] or anterior["weather_date"].astimezone(FUSO).hour != 0:
                    raise ValueError("Clima legado com grafia/calendário divergente no período. Normalize-o antes da carga ou use uma instância de desenvolvimento limpa.")
    for dispositivo in cenario.dispositivos:
        consulta = {"device_id": dispositivo["device_id"], "window_started_at": {"$lt": horario(cenario.fim)},
                    "window_finished_at": {"$gt": horario(cenario.inicio)}}
        vistos = set()
        for anterior in colecoes["consumption_summary"].find(consulta):
            inicio, fim = anterior["window_started_at"], anterior["window_finished_at"]
            chave = (inicio, fim)
            if (chave in vistos or (fim-inicio).total_seconds() != 300 or inicio.minute % 5 or inicio.second or inicio.microsecond):
                raise ValueError("Consumo legado duplicado/sobreposto ou fora da grade de cinco minutos. Corrija o período antes de carregar.")
            vistos.add(chave)


def executar(argv=None):
    parser = argparse.ArgumentParser(description="Gera um cenário BI sintético consistente com o catálogo SQL.")
    parser.add_argument("--contexto", required=True, help="JSON exportado por sql/exportar-contexto-bi.sql")
    parser.add_argument("--inicio", required=True, type=date.fromisoformat)
    parser.add_argument("--fim", type=date.fromisoformat, default=datetime.now(FUSO).date(), help="dia final exclusivo; padrão hoje, sem incluir o dia em andamento")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        cenario = Cenario(carregar_contexto(args.contexto), args.inicio, args.fim, args.seed)
        if not any(cenario.ativo(d, args.fim - timedelta(days=1)) for d in cenario.dispositivos):
            raise ValueError("Não há dispositivo instalado/vinculado no período selecionado.")
        colecoes = {}
        if not args.dry_run:
            from pathlib import Path
            if Path(args.contexto).resolve() == EXEMPLO.resolve():
                raise ValueError("O contexto de exemplo é fictício e só pode ser usado com --dry-run.")
            colecoes = {nome: obter_colecao(banco, nome) for nome, (banco, _) in COLECOES.items()}
            preflight(cenario, colecoes)
        resumo = {"simulation": True, "dry_run": args.dry_run, "seed": args.seed,
                  "inicio": str(args.inicio), "fim_exclusivo": str(args.fim),
                  "devices": len(cenario.dispositivos), "cities": [l["city"] for l in cenario.locais()], "collections": {}}
        for nome, (_, gerador) in COLECOES.items():
            documentos = iter(gerador.gerar_periodo(cenario))
            total, amostra = 0, None
            while lote := list(islice(documentos, 100)):
                if amostra is None:
                    amostra = lote[0]
                total += len(lote)
                if not args.dry_run:
                    operacoes = []
                    for documento in lote:
                        filtro = filtro_documento(nome, documento)
                        # IDs de sessões/feedbacks são estáveis. Nos demais, preserva o _id existente.
                        corpo = documento if set(filtro) == {"_id"} else {k: v for k, v in documento.items() if k != "_id"}
                        operacoes.append(ReplaceOne(filtro, corpo, upsert=True))
                    colecoes[nome].bulk_write(operacoes, ordered=True)
            resumo["collections"][nome] = {"documents": total, "sample": amostra}
            if not args.dry_run:
                print(f"{nome}: {total} documento(s) processado(s).", file=sys.stderr)
        print(json_util.dumps(resumo, indent=2))
        return 0
    except (ValueError, OSError, ConfiguracaoMongoError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
