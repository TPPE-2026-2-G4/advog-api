from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.atuacao.schema import AtuacaoResponse
from app.cargo.schema import CargoResponse
from app.funcionario.model import StatusFuncionario


class FuncionarioBase(BaseModel):
    nome: str
    email: str


class FuncionarioCreate(FuncionarioBase):
    cargo_id: int
    atuacao_id: int | None = None


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


class FuncionarioPerfilUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    uf_oab: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        validation_alias=AliasChoices("uf_oab", "ufOab"),
    )
    numero_oab: str | None = Field(
        default=None,
        min_length=5,
        max_length=5,
        validation_alias=AliasChoices("numero_oab", "numeroOab"),
    )
    atuacao_id: int | None = Field(default=None, gt=0)
    senha_atual: str | None = Field(
        default=None, validation_alias=AliasChoices("senha_atual", "senhaAtual")
    )
    nova_senha: str | None = Field(
        default=None,
        min_length=8,
        validation_alias=AliasChoices("nova_senha", "novaSenha"),
    )
    confirmar_nova_senha: str | None = Field(
        default=None,
        min_length=8,
        validation_alias=AliasChoices("confirmar_nova_senha", "confirmarNovaSenha"),
    )

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, nome: str | None) -> str | None:
        if nome is not None and not nome.strip():
            raise ValueError("O nome não pode ficar vazio")
        return nome.strip() if nome is not None else None

    @model_validator(mode="after")
    def validar_troca_senha(self):
        if "nome" in self.model_fields_set and self.nome is None:
            raise ValueError("O nome não pode ser nulo")

        campos_senha = (self.senha_atual, self.nova_senha, self.confirmar_nova_senha)
        if any(campo is not None for campo in campos_senha):
            if not all(campo is not None for campo in campos_senha):
                raise ValueError("Informe a senha atual, a nova senha e sua confirmação")
            if self.nova_senha != self.confirmar_nova_senha:
                raise ValueError("A confirmação da nova senha não confere")
        return self


class FuncionarioResponse(FuncionarioBase):
    cargo_id: int
    atuacao_id: int | None
    foto_perfil: int
    foto_perfil_url: str | None = None
    cargo: CargoResponse | None = None
    exibicao_institucional: bool = Field(default=False, alias="exibicaoInstitucional")
    receber_emails: bool = Field(default=True)
    funcionario_id: int
    numero_oab: str | None = None
    status: StatusFuncionario
    uf_oab: str | None = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FuncionarioPerfilResponse(FuncionarioResponse):
    atuacao: AtuacaoResponse | None = None

    @field_validator("receber_emails", mode="before")
    @classmethod
    def _default_receber_emails(cls, valor: bool | None) -> bool:
        return True if valor is None else valor


class FuncionarioInstitucionalResponse(BaseModel):
    """Dados públicos de um membro da equipe, exibidos nos cards da página institucional.

    Mantém os mesmos nomes de campo que o frontend já lê (``funcionario_id``, ``nome``,
    ``cargo``, ``atuacao``, ``uf_oab``, ``numero_oab`` e ``foto_perfil_url``), mas expõe
    ``cargo`` e ``atuacao`` apenas como o nome (texto) e omite e-mail, status, permissões
    e demais dados internos.
    """

    funcionario_id: int
    nome: str
    cargo: str | None = None
    atuacao: str | None = None
    uf_oab: str | None = None
    numero_oab: str | None = None
    foto_perfil_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("cargo", mode="before")
    @classmethod
    def _extrair_nome_cargo(cls, cargo: Any) -> str | None:
        return getattr(cargo, "nome_cargo", cargo)

    @field_validator("atuacao", mode="before")
    @classmethod
    def _extrair_nome_atuacao(cls, atuacao: Any) -> str | None:
        return getattr(atuacao, "nome", atuacao)
