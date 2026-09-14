from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.repositories.lancamento import LancamentoRepository
from app.schemas.lancamento import (
    LancamentoCreate,
    LancamentoResponse,
    LancamentoStatusUpdate,
    LancamentoUpdate,
)
from app.services.lancamento import LancamentoService

router = APIRouter(prefix="/lancamentos", tags=["Finanças"])


def get_lancamento_service(db: Session = Depends(get_db)) -> LancamentoService:
    repository = LancamentoRepository(db)
    return LancamentoService(repository)


@router.get("/", response_model=list[LancamentoResponse])
def listar_lancamentos(service: LancamentoService = Depends(get_lancamento_service)):
    return service.list_lancamentos()


@router.post("/", response_model=LancamentoResponse, status_code=201)
def criar_lancamento(
    lancamento: LancamentoCreate, service: LancamentoService = Depends(get_lancamento_service)
):
    return service.create_lancamento(lancamento)


@router.put("/{lancamento_id}", response_model=LancamentoResponse)
def atualizar_lancamento(
    lancamento_id: int,
    lancamento: LancamentoUpdate,
    service: LancamentoService = Depends(get_lancamento_service),
):
    return service.update_lancamento(lancamento_id, lancamento)


@router.patch("/{lancamento_id}/status", response_model=LancamentoResponse)
def atualizar_status_lancamento(
    lancamento_id: int,
    status_update: LancamentoStatusUpdate,
    service: LancamentoService = Depends(get_lancamento_service),
):
    return service.update_status(lancamento_id, status_update)


@router.delete("/{lancamento_id}", status_code=204)
def remover_lancamento(
    lancamento_id: int, service: LancamentoService = Depends(get_lancamento_service)
):
    service.delete_lancamento(lancamento_id)
    return None
