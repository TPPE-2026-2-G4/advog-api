from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services.funcionario import FuncionarioService
from app.schemas.funcionario import FuncionarioCreate, FuncionarioPrimeiroAcesso, FuncionarioResponse

router = APIRouter(prefix="/funcionarios", tags=["Funcionários"])

@router.post("", response_model=FuncionarioResponse)
def criar_funcionario(dados: FuncionarioCreate, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        return service.criar_funcionario(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{funcionario_id}/primeiro-acesso", response_model=FuncionarioResponse)
def primeiro_acesso(funcionario_id: int, dados: FuncionarioPrimeiroAcesso, db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    try:
        return service.primeiro_acesso(funcionario_id, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))