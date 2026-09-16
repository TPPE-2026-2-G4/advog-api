from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.processo import ProcessoCreate, ProcessoFilter, ProcessoResponse
from app.services.processo import ProcessoService

router = APIRouter(prefix="/processos", tags=["Processos"])


def get_processo_service(db: Session = Depends(get_db)) -> ProcessoService:
    return ProcessoService(db)


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
