from typing import cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.dependencies import obter_funcionario_atual
from app.models.funcionario import Funcionario
from app.schemas.funcionario import (
    FuncionarioCreate,
    FuncionarioMudarCargo,
    FuncionarioPrimeiroAcesso,
    FuncionarioResponse,
    FuncionarioUpdate,
)
from app.services.funcionario import FuncionarioService
from app.utils.email import enviar_email_boas_vindas
from app.utils.seguranca import validar_token_primeiro_acesso

router = APIRouter(prefix="/funcionarios", tags=["Funcionários"])


@router.post("", response_model=FuncionarioResponse, status_code=201)
def criar_funcionario(
    dados: FuncionarioCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    service = FuncionarioService(db)
    try:
        funcionario = service.criar_funcionario(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    background_tasks.add_task(
        enviar_email_boas_vindas,
        cast(str, funcionario.email),
        cast(str, funcionario.nome),
        cast(int, funcionario.funcionario_id),
    )
    return funcionario


@router.get("", response_model=list[FuncionarioResponse])
def buscar_todos_funcionarios(db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    funcionarios = service.buscar_todos()
    return funcionarios


@router.patch("/primeiro-acesso", response_model=FuncionarioResponse)
def primeiro_acesso(dados: FuncionarioPrimeiroAcesso, db: Session = Depends(get_db)):
    try:
        funcionario_id = validar_token_primeiro_acesso(dados.token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    service = FuncionarioService(db)
    try:
        funcionario = service.primeiro_acesso(funcionario_id, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return funcionario


@router.patch("/{funcionario_id}/mudar-cargo", response_model=FuncionarioResponse)
def mudar_cargo(funcionario_id: int, dados: FuncionarioMudarCargo, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        funcionario = service.mudar_cargo(funcionario_id, dados.cargo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return funcionario


@router.patch("", response_model=FuncionarioResponse)
def editar_dados(
    dados: FuncionarioUpdate,
    funcionario_atual: Funcionario = Depends(obter_funcionario_atual),
    db: Session = Depends(get_db),
):
    service = FuncionarioService(db)
    try:
        funcionario = service.editar_dados(funcionario_atual.funcionario_id, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return funcionario


@router.patch("/{funcionario_id}/mudar-acesso", response_model=FuncionarioResponse)
def mudar_acesso(funcionario_id: int, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        funcionario = service.mudar_acesso(funcionario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return funcionario


@router.delete("/{funcionario_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_funcionario(funcionario_id: int, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        service.apagar_funcionario(funcionario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
