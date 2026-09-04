from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services.funcionario import FuncionarioService
from app.schemas.funcionario import FuncionarioCreate, FuncionarioPrimeiroAcesso, FuncionarioResponse
from app.utils.email import enviar_email_boas_vindas

router = APIRouter(prefix="/funcionarios", tags=["Funcionários"])

@router.post("", response_model=FuncionarioResponse)
def criar_funcionario(
        dados: FuncionarioCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
    ):
    service = FuncionarioService(db)
    try:
        funcionario = service.criar_funcionario(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    background_tasks.add_task(enviar_email_boas_vindas, funcionario.email, funcionario.nome)
    return funcionario

@router.patch("/{funcionario_id}/primeiro-acesso", response_model=FuncionarioResponse)
def primeiro_acesso(funcionario_id: int, dados: FuncionarioPrimeiroAcesso, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        funcionario = service.primeiro_acesso(funcionario_id, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return funcionario

@router.get("", response_model=list[FuncionarioResponse])
def buscar_todos_funcionarios(db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    funcionarios = service.buscar_todos()
    return funcionarios