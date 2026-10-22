from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import obter_funcionario_atual
from app.lancamento.repository import LancamentoRepository
from app.lancamento.schema import (
    LancamentoCalendarioResponse,
    LancamentoCreate,
    LancamentoFilter,
    LancamentoPaginadoResponse,
    LancamentoResponse,
    LancamentoResumo,
    LancamentoUpdate,
)
from app.lancamento.service import LancamentoCalendarioService, LancamentoService

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


@router.patch("/{lancamento_id}/alternar-status", response_model=LancamentoResponse)
def alternar_status_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    try:
        return LancamentoService(db).alternar_status(lancamento_id)
    except ValueError as e:
        raise _erro_http(e) from e


@router.delete("/{lancamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    try:
        LancamentoService(db).deletar_lancamento(lancamento_id)
    except ValueError as e:
        raise _erro_http(e) from e


@router.get("/calendario", response_model=list[LancamentoCalendarioResponse])
def obter_calendario(filtros: LancamentoFilter = Depends(), db: Session = Depends(get_db)):
    try:
        repositorio = LancamentoRepository(db)
        return LancamentoCalendarioService(repositorio).obter_calendario(filtros)
    except ValueError as e:
        raise _erro_http(e) from e


@router.get("/calendario/exportar", response_class=Response)
def exportar_icalendar(filtros: LancamentoFilter = Depends(), db: Session = Depends(get_db)):
    try:
        repositorio = LancamentoRepository(db)
        conteudo_ics = LancamentoCalendarioService(repositorio).exportar_icalendar(filtros)
        headers = {"Content-Disposition": 'attachment; filename="calendario_financeiro.ics"'}
        return Response(
            content=conteudo_ics,
            media_type="text/calendar; charset=utf-8",
            headers=headers,
        )
    except ValueError as e:
        raise _erro_http(e) from e
