from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.processo.schema import (
    ProcessoCreate,
    ProcessoFilter,
    ProcessoResponse,
    SincronizacaoResponse,
)
from app.processo.service import ProcessoService

router = APIRouter(prefix="/processos", tags=["Processos"])


def get_processo_service(db: Session = Depends(get_db)) -> ProcessoService:
    return ProcessoService(db)


@router.post("/sincronizar", response_model=SincronizacaoResponse)
async def sincronizar_processos():
    """Aciona a sincronização de processos com a API Pública do Datajud."""
    total = await ProcessoService.sincronizar_processos_com_api()
    return SincronizacaoResponse(
        atualizados=total,
        mensagem=f"{total} processos sincronizados com sucesso via Datajud.",
    )


@router.post("/", response_model=ProcessoResponse, status_code=201)
def criar_processo(
    processo: ProcessoCreate, service: ProcessoService = Depends(get_processo_service)
):
    return service.create_processo(processo)


@router.get("/", response_model=list[ProcessoResponse])
def filtrar_processos(
    filtros: ProcessoFilter = Depends(), service: ProcessoService = Depends(get_processo_service)
):
    """
    Lista e filtra processos com base nos parâmetros informados na query string.
    """
    return service.search_processos(filtros)
