from pydantic import BaseModel, ConfigDict, Field
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
    uf_oab: Optional[str] = Field(default=None, min_length=2, max_length=2)
    numero_oab: Optional[str] = Field(default=None, min_length=5, max_length=5)

class FuncionarioResponse(FuncionarioBase):
    funcionario_id: int
    status: StatusFuncionario
    uf_oab: Optional[str] = None
    numero_oab: Optional[str] = None
    exibicaoInstitucional: bool = False

    model_config = ConfigDict(from_attributes=True)