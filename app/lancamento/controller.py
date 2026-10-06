from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.lancamento.schema import (
    LancamentoCreate,
    LancamentoResponse,
    LancamentoStatusUpdate,
    LancamentoUpdate,
)
from app.lancamento.service import (
    LancamentoNaoEncontradoError,
    LancamentoService,
    StatusLancamentoInvalidoError,
    TipoLancamentoInvalidoError,
)

router = APIRouter(prefix="/lancamentos", tags=["Finanças"])


@router.get("/", response_model=list[LancamentoResponse])
def listar_lancamentos(db: Session = Depends(get_db)):
    service = LancamentoService(db)
    return service.list_lancamentos()


@router.post("/", response_model=LancamentoResponse, status_code=201)
def criar_lancamento(lancamento: LancamentoCreate, db: Session = Depends(get_db)):
    service = LancamentoService(db)
    try:
        return service.create_lancamento(lancamento)
    except TipoLancamentoInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{lancamento_id}", response_model=LancamentoResponse)
def atualizar_lancamento(
    lancamento_id: int,
    lancamento: LancamentoUpdate,
    db: Session = Depends(get_db),
):
    service = LancamentoService(db)
    try:
        return service.update_lancamento(lancamento_id, lancamento)
    except LancamentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except TipoLancamentoInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{lancamento_id}/status", response_model=LancamentoResponse)
def atualizar_status_lancamento(
    lancamento_id: int,
    status_update: LancamentoStatusUpdate,
    db: Session = Depends(get_db),
):
    service = LancamentoService(db)
    try:
        return service.update_status(lancamento_id, status_update)
    except LancamentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except StatusLancamentoInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{lancamento_id}", status_code=204)
def remover_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    service = LancamentoService(db)
    try:
        service.delete_lancamento(lancamento_id)
    except LancamentoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return None
