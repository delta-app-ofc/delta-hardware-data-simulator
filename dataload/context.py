"""Catálogo SQL e calendário compartilhados pelos simuladores de BI."""

import hashlib
import json
import math
import random
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from bson import ObjectId

FUSO = ZoneInfo("America/Sao_Paulo")
EXEMPLO = Path(__file__).parent / "fixtures" / "contexto-exemplo.json"


def texto(valor: str) -> str:
    """Preserva a grafia do SQL, normalizando caixa, Unicode e espaços."""
    return " ".join(unicodedata.normalize("NFC", valor).upper().split())


def chave_cidade(valor: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto(valor)) if not unicodedata.combining(c))


def aleatorio(seed: int, *chaves) -> random.Random:
    # A mesma observação mantém seus valores ao ampliar ou repetir o período.
    chave = json.dumps([seed, *map(str, chaves)], ensure_ascii=False)
    return random.Random(int.from_bytes(hashlib.sha256(chave.encode()).digest()[:8], "big"))


def identificador(colecao: str, *chaves) -> ObjectId:
    chave = json.dumps(["DELTA_SIM_BI_V1", colecao, *map(str, chaves)], ensure_ascii=False)
    return ObjectId(hashlib.sha256(chave.encode()).hexdigest()[:24])


def horario(dia: date, hora: int = 0) -> datetime:
    return datetime.combine(dia, time(hora), FUSO).astimezone(timezone.utc)


def carregar_contexto(caminho: str | Path) -> list[dict]:
    dados = json.loads(Path(caminho).read_text(encoding="utf-8-sig"))
    dispositivos = dados.get("devices") if isinstance(dados, dict) else dados
    if not isinstance(dispositivos, list) or not dispositivos:
        raise ValueError("O contexto deve conter uma lista devices não vazia, exportada do SQL.")
    if len(dispositivos) > 1000:
        raise ValueError("Selecione no máximo 1000 dispositivos por cenário BI.")
    vistos, propriedades, regioes, cidades = set(), {}, {}, {}
    resultado = []
    for original in dispositivos:
        item = original.copy()
        for campo in ("device_id", "region_name", "city", "state", "classification_group"):
            if not isinstance(item.get(campo), str) or not item[campo].strip():
                raise ValueError(f"Contexto: {campo} obrigatório e não vazio.")
        # device_id é identidade de FK lógica, não se altera sua grafia.
        if item["device_id"] != item["device_id"].strip() or item["device_id"] in vistos:
            raise ValueError("device_id repetido ou com espaços nas extremidades.")
        vistos.add(item["device_id"])
        for campo in ("user_id", "property_id", "region_id"):
            if type(item.get(campo)) is not int or not 0 < item[campo] < 2**31:
                raise ValueError(f"Contexto: {campo} deve ser um ID SQL inteiro positivo int32.")
        for campo in ("region_name", "city", "state", "classification_group"):
            item[campo] = texto(item[campo])
        if item["state"] != "SP" or item["classification_group"] not in ("RESIDENCIAL", "COMERCIAL"):
            raise ValueError("O cenário BI exige imóveis SP residenciais/comerciais.")
        for campo, limite in (("latitude", 90), ("longitude", 180)):
            valor = item.get(campo)
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or abs(valor) > limite:
                raise ValueError(f"Contexto: {campo} ausente ou inválida; corrija o endereço no SQL.")
            item[campo] = float(valor)
        if item["latitude"] == item["longitude"] == 0:
            raise ValueError("Coordenadas (0,0) não identificam um imóvel SP.")
        for campo in ("installation_date", "association_date"):
            try:
                item[campo] = date.fromisoformat(item[campo])
            except (KeyError, TypeError, ValueError) as erro:
                raise ValueError(f"Contexto: {campo} deve ter formato YYYY-MM-DD.") from erro
        assinatura = tuple(item[c] for c in ("region_id", "region_name", "city", "classification_group", "latitude", "longitude"))
        if item["property_id"] in propriedades and propriedades[item["property_id"]] != assinatura:
            raise ValueError("O mesmo imóvel tem cadastros conflitantes no contexto.")
        propriedades[item["property_id"]] = assinatura
        if item["region_id"] in regioes and regioes[item["region_id"]] != item["region_name"]:
            raise ValueError("O mesmo ID de região tem nomes conflitantes.")
        regioes[item["region_id"]] = item["region_name"]
        chave = chave_cidade(item["city"])
        if chave in cidades and cidades[chave] != item["city"]:
            raise ValueError("Há grafias divergentes para a mesma cidade; padronize o catálogo SQL.")
        cidades[chave] = item["city"]
        resultado.append(item)
    return sorted(resultado, key=lambda item: item["device_id"])


@dataclass
class Cenario:
    dispositivos: list[dict]
    inicio: date
    fim: date
    seed: int = 42

    def __post_init__(self):
        if not 1 <= (self.fim - self.inicio).days <= 366:
            raise ValueError("O período deve conter de 1 a 366 dias completos; fim é exclusivo.")
        if self.fim > datetime.now(FUSO).date():
            raise ValueError("O fim não pode incluir dias futuros ou o dia ainda em andamento.")
        if self.inicio.year < 2020:
            raise ValueError("Use datas a partir de 2020 (dias civis SP de 24 horas).")

    def dias(self):
        for indice in range((self.fim - self.inicio).days):
            yield self.inicio + timedelta(days=indice)

    def ativo(self, dispositivo, dia):
        return dia >= max(dispositivo["installation_date"], dispositivo["association_date"])

    def usuarios(self):
        return sorted({d["user_id"] for d in self.dispositivos})

    def locais(self):
        # Um ponto climático por cidade, escolhido deterministicamente de um endereço SQL.
        locais = {}
        for item in self.dispositivos:
            locais.setdefault(item["city"], {k: item[k] for k in ("city", "state", "latitude", "longitude")})
        return list(locais.values())


def exemplo() -> Cenario:
    fim = datetime.now(FUSO).date()
    return Cenario(carregar_contexto(EXEMPLO), fim - timedelta(days=100), fim)
