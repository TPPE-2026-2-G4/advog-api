from typing import cast

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import exigir_permissao, obter_funcionario_atual
from app.core.email import enviar_email_boas_vindas
from app.core.seguranca import validar_token_primeiro_acesso
from app.funcionario.model import Funcionario
from app.funcionario.schema import (
    FuncionarioCreate,
    FuncionarioMudarCargo,
    FuncionarioMudarExibicao,
    FuncionarioPerfilResponse,
    FuncionarioPerfilUpdate,
    FuncionarioPrimeiroAcesso,
    FuncionarioResponse,
    FuncionarioUpdate,
)
from app.funcionario.service import FuncionarioService

router = APIRouter(prefix="/funcionarios", tags=["Funcionários"])


@router.post(
    "",
    response_model=FuncionarioResponse,
    status_code=201,
    dependencies=[Depends(exigir_permissao("gerenciar_equipe"))],
)
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


@router.get("/perfil", response_model=FuncionarioPerfilResponse)
def obter_meu_perfil(
    funcionario_atual: Funcionario = Depends(obter_funcionario_atual),
):
    return funcionario_atual


@router.patch("/perfil", response_model=FuncionarioPerfilResponse)
def editar_meu_perfil(
    dados: FuncionarioPerfilUpdate,
    funcionario_atual: Funcionario = Depends(obter_funcionario_atual),
    db: Session = Depends(get_db),
):
    try:
        return FuncionarioService(db).editar_perfil(funcionario_atual.funcionario_id, dados)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/perfil/foto", response_model=FuncionarioPerfilResponse)
def atualizar_minha_foto(
    file: UploadFile = File(...),
    funcionario_atual: Funcionario = Depends(obter_funcionario_atual),
    db: Session = Depends(get_db),
):
    try:
        return FuncionarioService(db).atualizar_foto_perfil(funcionario_atual.funcionario_id, file)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


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


@router.patch(
    "/{funcionario_id}/mudar-acesso",
    response_model=FuncionarioResponse,
    dependencies=[Depends(exigir_permissao("gerenciar_equipe"))],
)
def mudar_acesso(funcionario_id: int, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        funcionario = service.mudar_acesso(funcionario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return funcionario


@router.patch(
    "/{funcionario_id}/mudar-cargo",
    response_model=FuncionarioResponse,
    dependencies=[Depends(exigir_permissao("gerenciar_equipe"))],
)
def mudar_cargo(funcionario_id: int, dados: FuncionarioMudarCargo, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        funcionario = service.mudar_cargo(funcionario_id, dados.cargo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return funcionario


@router.patch(
    "/{funcionario_id}/exibicao-institucional",
    response_model=FuncionarioResponse,
    dependencies=[Depends(exigir_permissao("gerenciar_equipe"))],
)
def mudar_exibicao_institucional(
    funcionario_id: int,
    dados: FuncionarioMudarExibicao,
    db: Session = Depends(get_db),
):
    service = FuncionarioService(db)
    try:
        return service.mudar_exibicao_institucional(funcionario_id, dados.exibicao_institucional)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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


@router.delete(
    "/{funcionario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(exigir_permissao("gerenciar_equipe"))],
)
def apagar_funcionario(funcionario_id: int, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        service.apagar_funcionario(funcionario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
