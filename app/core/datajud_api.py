import logging
import os
import random
import re
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Mapeamento do dígito J.TR (posições 13 a 16 no CNJ sem formatação: NNNNNNNDDAAAAJTROOOO)
# J: Justiça (8: Estadual, 4: Federal, 5: Trabalho, 1: STF, 2: CNJ, 3: STJ, 9: Militar)
# TR: Tribunal
TRIBUNAIS_MAP: dict[tuple[str, str], str] = {
    # Justiça Estadual (J=8)
    ("8", "01"): "tjac",
    ("8", "02"): "tjal",
    ("8", "03"): "tjap",
    ("8", "04"): "tjam",
    ("8", "05"): "tjba",
    ("8", "06"): "tjce",
    ("8", "07"): "tjdft",
    ("8", "08"): "tjes",
    ("8", "09"): "tjgo",
    ("8", "10"): "tjma",
    ("8", "11"): "tjmt",
    ("8", "12"): "tjms",
    ("8", "13"): "tjmg",
    ("8", "14"): "tjpa",
    ("8", "15"): "tjpb",
    ("8", "16"): "tjpr",
    ("8", "17"): "tjpe",
    ("8", "18"): "tjpi",
    ("8", "19"): "tjrj",
    ("8", "20"): "tjrn",
    ("8", "21"): "tjrs",
    ("8", "22"): "tjro",
    ("8", "23"): "tjrr",
    ("8", "24"): "tjsc",
    ("8", "25"): "tjse",
    ("8", "26"): "tjsp",
    ("8", "27"): "tjto",
    # Justiça Federal (J=4)
    ("4", "01"): "trf1",
    ("4", "02"): "trf2",
    ("4", "03"): "trf3",
    ("4", "04"): "trf4",
    ("4", "05"): "trf5",
    ("4", "06"): "trf6",
    # Justiça do Trabalho (J=5)
    ("5", "01"): "trt1",
    ("5", "02"): "trt2",
    ("5", "03"): "trt3",
    ("5", "04"): "trt4",
    ("5", "15"): "trt15",
}

DEFAULT_DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="


class DatajudApiClient:
    """Client para integração com a API Pública do Datajud (CNJ)."""

    def __init__(self) -> None:
        self.api_key = os.getenv("DATAJUD_API_KEY", DEFAULT_DATAJUD_API_KEY)
        self.base_url = os.getenv("DATAJUD_BASE_URL", "https://api-publica.datajud.cnj.jus.br")
        # Modo mock pode ser ativado explicitamente via variável DATAJUD_MOCK=true
        self.is_mock = os.getenv("DATAJUD_MOCK", "false").lower() in ("true", "1", "yes")

    @staticmethod
    def sanitizar_cnj(cnj: str) -> str:
        """Remove pontuações e caracteres não numéricos do CNJ."""
        return re.sub(r"\D", "", cnj or "")

    @classmethod
    def extrair_alias_tribunal(cls, cnj_limpo: str) -> str | None:
        """Extrai o alias do tribunal correspondente ao número CNJ (20 dígitos).

        Formato: NNNNNNN-DD.AAAA.J.TR.OOOO -> NNNNNNNDDAAAAJTROOOO
        Indices 0-indexed:
          - NNNNNNN: [0:7]
          - DD: [7:9]
          - AAAA: [9:13]
          - J: [13:14]
          - TR: [14:16]
          - OOOO: [16:20]
        """
        if len(cnj_limpo) != 20:
            return None
        j = cnj_limpo[13:14]
        tr = cnj_limpo[14:16]
        return TRIBUNAIS_MAP.get((j, tr))

    async def fetch_processo(self, cnj: str) -> dict[str, Any] | None:
        """Consulta dados atualizados de um processo via API Pública do Datajud.

        Retorna dicionário com status, tribunal e data_realizado ou None em caso de falha.
        """
        cnj_limpo = self.sanitizar_cnj(cnj)
        if not cnj_limpo:
            return None

        if self.is_mock:
            return self._mock_fetch_processo(cnj_limpo)

        tribunal_alias = self.extrair_alias_tribunal(cnj_limpo)
        if not tribunal_alias:
            logger.warning(f"Tribunal não identificado a partir do CNJ {cnj_limpo}.")
            return None

        url = f"{self.base_url}/api_publica_{tribunal_alias}/_search"
        headers = {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"query": {"match": {"numeroProcesso": cnj_limpo}}}

        try:
            async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                hits = data.get("hits", {}).get("hits", [])
                if not hits:
                    logger.info(f"Nenhum processo encontrado no Datajud para o CNJ {cnj_limpo}.")
                    return None

                primeiro_hit = hits[0].get("_source", {})
                tribunal_sigla = primeiro_hit.get("tribunal") or tribunal_alias.upper()

                # Busca status e data a partir do último movimento registrado
                movimentos = (
                    primeiro_hit.get("dadosBasicos", {}).get("movimento")
                    or primeiro_hit.get("movimentos")
                    or []
                )

                status_atual = "Em Andamento"
                data_movimento = None
                if movimentos:
                    ultimo_mov = movimentos[-1]
                    status_atual = ultimo_mov.get("nome") or status_atual
                    data_hora_str = ultimo_mov.get("dataHora")
                    if data_hora_str:
                        try:
                            # Formato ISO (ex: 2024-06-27T10:30:05.000Z)
                            clean_dt_str = data_hora_str.replace("Z", "+00:00")
                            data_movimento = datetime.fromisoformat(clean_dt_str)
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Formato de dataHora inválido no movimento: {data_hora_str}"
                            )

                return {
                    "status": status_atual,
                    "tribunal": tribunal_sigla,
                    "data_realizado": data_movimento,
                }
        except Exception as e:
            logger.warning(f"Erro ou timeout ao buscar processo {cnj_limpo} no Datajud: {e}.")
            return None

    def _mock_fetch_processo(self, cnj: str) -> dict[str, Any]:
        """Retorno simulado para testes e desenvolvimento offline."""
        status_options = [
            "Em Andamento",
            "Arquivado",
            "Concluso para Decisão",
            "Em Recurso",
            "Julgado",
        ]
        alias = self.extrair_alias_tribunal(cnj)
        tribunal_sigla = alias.upper() if alias else "TJSP"

        return {
            "status": random.choice(status_options),
            "tribunal": tribunal_sigla,
            "data_realizado": datetime.now(UTC),
        }
