from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import obter_funcionario_atual
from app.lancamento.schema import (
    LancamentoCreate,
    LancamentoFilter,
    LancamentoPaginadoResponse,
    LancamentoResponse,
    LancamentoResumo,
    LancamentoStatusUpdate,
    LancamentoUpdate,
)
from app.lancamento.service import LancamentoService

router = APIRouter(
    prefix="/lancamentos",
    tags=["Lançamentos"],
    dependencies=[Depends(obter_funcionario_atual)],
)

_NAO_ENCONTRADO = (
    "Lançamento não encontrado",
    "Categoria não encontrada",
    "Cliente não encontrado",
)


def _erro_http(e: ValueError) -> HTTPException:
    status_code = (
        status.HTTP_404_NOT_FOUND if str(e) in _NAO_ENCONTRADO else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=status_code, detail=str(e))


@router.get("/", response_model=list[LancamentoResponse])
def listar_lancamentos(filtros: LancamentoFilter = Depends(), db: Session = Depends(get_db)):
    try:
        return LancamentoService(db).listar_lancamentos(filtros)
    except ValueError as e:
        raise _erro_http(e) from e


@router.get("/paginado", response_model=LancamentoPaginadoResponse)
def listar_lancamentos_paginado(
    filtros: LancamentoFilter = Depends(),
    page: int = Query(1, ge=1, description="Página a ser retornada"),
    page_size: int = Query(10, ge=1, le=100, description="Quantidade de itens por página"),
    db: Session = Depends(get_db),
):
    try:
        return LancamentoService(db).listar_lancamentos_paginado(filtros, page, page_size)
    except ValueError as e:
        raise _erro_http(e) from e


@router.get("/resumo", response_model=LancamentoResumo)
def resumir_lancamentos(filtros: LancamentoFilter = Depends(), db: Session = Depends(get_db)):
    try:
        return LancamentoService(db).resumir_lancamentos(filtros)
    except ValueError as e:
        raise _erro_http(e) from e


@router.post("/", response_model=LancamentoResponse, status_code=status.HTTP_201_CREATED)
def criar_lancamento(dados: LancamentoCreate, db: Session = Depends(get_db)):
    try:
        return LancamentoService(db).criar_lancamento(dados)
    except ValueError as e:
        raise _erro_http(e) from e


@router.put("/{lancamento_id}", response_model=LancamentoResponse)
def atualizar_lancamento(
    lancamento_id: int, dados: LancamentoUpdate, db: Session = Depends(get_db)
):
    try:
        return LancamentoService(db).atualizar_lancamento(lancamento_id, dados)
    except ValueError as e:
        raise _erro_http(e) from e


@router.patch("/{lancamento_id}/status", response_model=LancamentoResponse)
def atualizar_status_lancamento(
    lancamento_id: int, dados: LancamentoStatusUpdate, db: Session = Depends(get_db)
):
    try:
        return LancamentoService(db).atualizar_status(lancamento_id, dados)
    except ValueError as e:
        raise _erro_http(e) from e


@router.delete("/{lancamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    try:
        LancamentoService(db).deletar_lancamento(lancamento_id)
    except ValueError as e:
        raise _erro_http(e) from e
