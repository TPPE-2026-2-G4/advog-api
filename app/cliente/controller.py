from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.cliente.schema import (
    ClienteCreate,
    ClienteFilter,
    ClientePaginadoFilter,
    ClientePaginadoResponse,
    ClienteResponse,
    ClienteUpdate,
)
from app.cliente.service import ClienteNaoEncontradoError, ClienteService
from app.config.database import get_db
from app.config.limiter import limiter
from app.core.dependencies import exigir_permissao
from app.core.permissoes import ACESSO_LISTA_CLIENTES

router = APIRouter(prefix="/clientes", tags=["Clientes"])

LER_CLIENTES = Depends(exigir_permissao(*ACESSO_LISTA_CLIENTES))


@router.get(
    "/",
    response_model=list[ClienteResponse],
    dependencies=[LER_CLIENTES],
)
def listar_clientes(
    filters: ClienteFilter = Depends(),
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    return service.search_clientes(filters)


@router.get(
    "/paginado",
    response_model=ClientePaginadoResponse,
    dependencies=[LER_CLIENTES],
)
def listar_clientes_paginado(
    filters: ClientePaginadoFilter = Depends(),
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    return service.search_clientes_paginado(filters)


@router.get(
    "/{cliente_id}",
    response_model=ClienteResponse,
    dependencies=[LER_CLIENTES],
)
def obter_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    try:
        return service.get_cliente_by_id(cliente_id)
    except ClienteNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/", response_model=ClienteResponse, status_code=201)
@limiter.limit("5/minute")
def criar_cliente(
    request: Request,
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    return service.create_cliente(cliente_data)


@router.put(
    "/{cliente_id}",
    response_model=ClienteResponse,
    dependencies=[Depends(exigir_permissao("gerenciar_clientes"))],
)
def atualizar_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    try:
        return service.update_cliente(cliente_id, cliente_data)
    except ClienteNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{cliente_id}",
    status_code=204,
    dependencies=[Depends(exigir_permissao("gerenciar_clientes"))],
)
def excluir_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    try:
        service.delete_cliente(cliente_id)
    except ClienteNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
