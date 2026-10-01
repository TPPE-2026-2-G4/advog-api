import logging
import os
import random
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)


class JusbrasilApiClient:
    def __init__(self):
        self.api_token = os.getenv("JUSBRASIL_API_TOKEN")
        self.base_url = "https://api.jusbrasil.com.br/v1"
        self.is_mock = not bool(self.api_token)

    async def fetch_processo(self, cnj: str) -> dict | None:

        if self.is_mock:
            return self._mock_fetch_processo(cnj)

        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.api_token}"}
                response = await client.get(f"{self.base_url}/processos/{cnj}", headers=headers)
                response.raise_for_status()
                data = response.json()

                return {
                    "status": data.get("situacao"),
                    "tribunal": data.get("tribunal", {}).get("sigla"),
                    "data_realizado": datetime.now(UTC),
                }
        except Exception as e:
            logger.error(f"Erro ao buscar processo {cnj} no Jusbrasil: {e}")
            return None

    def _mock_fetch_processo(self, cnj: str) -> dict:

        status_options = ["Em Andamento", "Arquivado", "Concluso para Decisão", "Em Recurso"]
        return {
            "status": random.choice(status_options),
            "data_realizado": datetime.now(UTC),
        }
