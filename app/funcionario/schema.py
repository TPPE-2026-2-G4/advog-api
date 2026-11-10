from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.cargo.schema import CargoResponse
from app.funcionario.model import StatusFuncionario


class FuncionarioBase(BaseModel):
    nome: str
    email: str


class FuncionarioCreate(FuncionarioBase):
    cargo_id: int
    atuacao_id: int


class FuncionarioPrimeiroAcesso(BaseModel):
    token: str
    nome: str | None = None
    senha: str
    uf_oab: str | None = Field(default=None, min_length=2, max_length=2)
    numero_oab: str | None = Field(default=None, min_length=5, max_length=5)


class FuncionarioMudarCargo(BaseModel):
    cargo_id: int


class FuncionarioMudarExibicao(BaseModel):
    exibicao_institucional: bool = Field(..., alias="exibicaoInstitucional")
    model_config = ConfigDict(populate_by_name=True)


class FuncionarioMudarReceberEmails(BaseModel):
    receber_emails: bool = Field(..., alias="receberEmails")
    model_config = ConfigDict(populate_by_name=True)


class FuncionarioUpdate(BaseModel):
    nome: str | None = None
    senha: str | None = None
    uf_oab: str | None = Field(default=None, min_length=2, max_length=2)
    numero_oab: str | None = Field(default=None, min_length=5, max_length=5)
    receber_emails: bool | None = None


class FuncionarioResponse(FuncionarioBase):
    cargo_id: int
    atuacao_id: int
    foto_perfil: int
    cargo: CargoResponse | None = None
    exibicao_institucional: bool = Field(default=False, alias="exibicaoInstitucional")
    receber_emails: bool = Field(default=True)
    funcionario_id: int
    numero_oab: str | None = None
    status: StatusFuncionario
    uf_oab: str | None = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("receber_emails", mode="before")
    @classmethod
    def _default_receber_emails(cls, valor: bool | None) -> bool:
        return True if valor is None else valor
