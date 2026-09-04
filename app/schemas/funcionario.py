from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.models.funcionario import StatusFuncionario

class FuncionarioBase(BaseModel):
    nome: str
    email: str
  
class FuncionarioCreate(FuncionarioBase):
    pass

class FuncionarioPrimeiroAcesso(BaseModel):
    nome: Optional[str] = None
    senha: str
    uf_oab: Optional[str] = None
    numero_oab: Optional[str] = None

class FuncionarioResponse(FuncionarioBase):
    funcionario_id: int
    status: StatusFuncionario
    uf_oab: Optional[str] = None
    numero_oab: Optional[str] = None

    class Config:
        model_config = ConfigDict(from_attributes=True)