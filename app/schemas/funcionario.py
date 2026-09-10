from pydantic import BaseModel, ConfigDict, Field

from app.models.funcionario import StatusFuncionario
from app.schemas.cargo import CargoResponse


class FuncionarioBase(BaseModel):
    nome: str
    email: str


class FuncionarioCreate(FuncionarioBase):
    cargo_id: int


class FuncionarioPrimeiroAcesso(BaseModel):
    nome: str | None = None
    senha: str
    uf_oab: str | None = Field(default=None, min_length=2, max_length=2)
    numero_oab: str | None = Field(default=None, min_length=5, max_length=5)


class FuncionarioResponse(FuncionarioBase):
    cargo_id: int
    cargo: CargoResponse | None = None
    exibicaoInstitucional: bool = False
    funcionario_id: int
    numero_oab: str | None = None
    status: StatusFuncionario
    uf_oab: str | None = None
    model_config = ConfigDict(from_attributes=True)
