from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.cliente.schema import ClienteCreate, ClienteFilter, ClienteResponse, ClienteUpdate
from app.cliente.service import ClienteNaoEncontradoError, ClienteService
from app.config.database import get_db
from app.core.dependencies import obter_funcionario_atual
from app.funcionario.model import Funcionario

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("/", response_model=list[ClienteResponse])
def listar_clientes(
    filters: ClienteFilter = Depends(),
    db: Session = Depends(get_db),
    current_user: Funcionario = Depends(obter_funcionario_atual),
):
    service = ClienteService(db)
    return service.search_clientes(filters)


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obter_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Funcionario = Depends(obter_funcionario_atual),
):
    service = ClienteService(db)
    try:
        return service.get_cliente_by_id(cliente_id)
    except ClienteNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/", response_model=ClienteResponse, status_code=201)
def criar_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: Funcionario = Depends(obter_funcionario_atual),
):
    service = ClienteService(db)
    return service.create_cliente(cliente_data)


@router.put("/{cliente_id}", response_model=ClienteResponse)
def atualizar_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: Funcionario = Depends(obter_funcionario_atual),
):
    service = ClienteService(db)
    try:
        return service.update_cliente(cliente_id, cliente_data)
    except ClienteNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{cliente_id}", status_code=204)
def excluir_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Funcionario = Depends(obter_funcionario_atual),
):
    service = ClienteService(db)
    try:
        service.delete_cliente(cliente_id)
    except ClienteNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
