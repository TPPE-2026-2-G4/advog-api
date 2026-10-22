from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.categoria_lancamento.schema import (
    CategoriaLancamentoCreate,
    CategoriaLancamentoResponse,
    CategoriaLancamentoUpdate,
)
from app.categoria_lancamento.service import CategoriaLancamentoService
from app.config.database import get_db
from app.core.dependencies import obter_funcionario_atual

router = APIRouter(
    prefix="/categorias-lancamento",
    tags=["Categorias de Lançamento"],
    dependencies=[Depends(obter_funcionario_atual)],
)


def _erro_http(e: ValueError) -> HTTPException:
    status_code = (
        status.HTTP_404_NOT_FOUND
        if str(e) == "Categoria não encontrada"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=status_code, detail=str(e))


@router.get("", response_model=list[CategoriaLancamentoResponse])
def listar_categorias(db: Session = Depends(get_db)):
    return CategoriaLancamentoService(db).buscar_todas()


@router.get("/{categoria_id}", response_model=CategoriaLancamentoResponse)
def buscar_categoria_por_id(categoria_id: int, db: Session = Depends(get_db)):
    try:
        return CategoriaLancamentoService(db).buscar_por_id(categoria_id)
    except ValueError as e:
        raise _erro_http(e) from e


@router.post("", response_model=CategoriaLancamentoResponse, status_code=status.HTTP_201_CREATED)
def criar_categoria(dados: CategoriaLancamentoCreate, db: Session = Depends(get_db)):
    try:
        return CategoriaLancamentoService(db).criar_categoria(dados)
    except ValueError as e:
        raise _erro_http(e) from e


@router.put("/{categoria_id}", response_model=CategoriaLancamentoResponse)
def atualizar_categoria(
    categoria_id: int, dados: CategoriaLancamentoUpdate, db: Session = Depends(get_db)
):
    try:
        return CategoriaLancamentoService(db).atualizar_categoria(categoria_id, dados)
    except ValueError as e:
        raise _erro_http(e) from e


@router.delete("/{categoria_id}", response_model=CategoriaLancamentoResponse)
def deletar_categoria(categoria_id: int, db: Session = Depends(get_db)):
    try:
        return CategoriaLancamentoService(db).deletar_categoria(categoria_id)
    except ValueError as e:
        raise _erro_http(e) from e
