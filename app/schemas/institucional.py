import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-F][6]$")


def _vazio_para_none(v: str | None) -> str | None:

    if isinstance(v, str) and v.strip() == "":
        return None
    return v


class InstitucionalBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome_escritorio: str = Field(..., min_length=2, max_length=150, alias="nomeEscritorio")
    descricao: str | None = Field(default=None, max_length=255)
    sobre_escritorio: str | None = Field(default=None, alias="sobreEscritorio")
    email: EmailStr | None = None
    telefone: str | None = Field(default=None, max_length=20)
    endereco: str | None = None
    cor_primaria: str = Field(..., alias="corPrimaria")
    cor_secundaria: str = Field(..., alias="corSecundaria")
    logotipo: str | None = None
    banner_hero: str | None = Field(default=None, alias="bannerHero")

    @field_validator("email", mode="before")
    @classmethod
    def _limpar_email(cls, v: str | None) -> str | None:
        return _vazio_para_none(v)

    @field_validator("cor_primaria", "cor_secundaria")
    @classmethod
    def _validar_hex(cls, v: str | None) -> str | None:
        if v is not None and not HEX_COLOR_PATTERN.match(v):
            raise ValueError("Cor deve estar no formato hexadecimal #RRGGBB (ex: #1E3A8A)")
        return v


class InstitucionalResponse(InstitucionalBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(validation_alias="institucional_id", serialization_alias="id")


class InstitucionalUploadResponse(BaseModel):
    url: str
