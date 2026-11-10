import asyncio
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.config import database
from app.config.storage import S3_BUCKET_PRIVADO, s3_client

router = APIRouter(tags=["Health"])

TIMEOUT_READINESS_SEGUNDOS = 3.0


def verificar_banco_conexao() -> None:
    with database.engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def verificar_storage_conexao() -> None:
    s3_client.head_bucket(Bucket=S3_BUCKET_PRIVADO)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Liveness Check",
    description="Endpoint leve para verificação de liveness (sem queries ao banco).",
)
def health_liveness() -> dict[str, str]:
    return {"status": "ok", "service": "advog-api"}


@router.get(
    "/health/ready",
    summary="Readiness Check",
    description="Verificação ativa de conexão com o banco de dados e storage com timeout de 3s.",
)
async def health_readiness(response: Response) -> dict[str, Any]:
    async def _checar_banco() -> str:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(verificar_banco_conexao),
                timeout=TIMEOUT_READINESS_SEGUNDOS,
            )
            return "ok"
        except TimeoutError:
            return "timeout: banco de dados não respondeu em 3s"
        except Exception as exc:
            return f"erro: {exc}"

    async def _checar_storage() -> str:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(verificar_storage_conexao),
                timeout=TIMEOUT_READINESS_SEGUNDOS,
            )
            return "ok"
        except TimeoutError:
            return "timeout: storage não respondeu em 3s"
        except Exception as exc:
            return f"erro: {exc}"

    db_status, storage_status = await asyncio.gather(_checar_banco(), _checar_storage())

    if db_status != "ok" or storage_status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database": db_status,
            "storage": storage_status,
        }

    return {
        "status": "ready",
        "database": db_status,
        "storage": storage_status,
    }
