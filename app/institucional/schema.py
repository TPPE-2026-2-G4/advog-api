import re
from typing import Any, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
)

from app.core.storage import obter_url_publica

HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def _vazio_para_none(texto: str | None) -> str | None:
    if isinstance(texto, str) and texto.strip() == "":
        return None
    return texto


class InstitucionalBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome_escritorio: str = Field(..., min_length=2, max_length=150, alias="nomeEscritorio")
    descricao: str | None = Field(default=None, max_length=255)
    sobre_escritorio: str | None = Field(default=None, alias="sobreEscritorio")
    imagem_sobre: str | None = Field(default=None, alias="imagemSobre")
    email: EmailStr | None = None
    telefone: str | None = Field(default=None, max_length=20)
    endereco: str | None = None
    cor_primaria: str = Field(..., alias="corPrimaria")
    cor_secundaria: str = Field(..., alias="corSecundaria")
    logotipo: str | None = None
    banner_hero: str | None = Field(default=None, alias="bannerHero")

    @field_validator("email", mode="before")
    @classmethod
    def _limpar_email(cls, email_bruto: str | None) -> str | None:
        return _vazio_para_none(email_bruto)

    @field_validator("cor_primaria", "cor_secundaria")
    @classmethod
    def _validar_hex(cls, cor_hex: str | None) -> str | None:
        if cor_hex is not None and not HEX_COLOR_PATTERN.match(cor_hex):
            raise ValueError("Cor deve estar no formato hexadecimal #RRGGBB (ex: #1E3A8A)")
        return cor_hex


class InstitucionalUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome_escritorio: str | None = Field(
        default=None, min_length=2, max_length=150, alias="nomeEscritorio"
    )
    descricao: str | None = Field(default=None, max_length=255)
    sobre_escritorio: str | None = Field(default=None, alias="sobreEscritorio")
    imagem_sobre: str | None = Field(default=None, alias="imagemSobre")
    email: EmailStr | None = None
    telefone: str | None = Field(default=None, max_length=20)
    endereco: str | None = None
    cor_primaria: str | None = Field(default=None, alias="corPrimaria")
    cor_secundaria: str | None = Field(default=None, alias="corSecundaria")

    @field_validator("email", mode="before")
    @classmethod
    def _limpar_email(cls, email_bruto: str | None) -> str | None:
        return _vazio_para_none(email_bruto)

    @field_validator("cor_primaria", "cor_secundaria")
    @classmethod
    def _validar_hex(cls, cor_hex: str | None) -> str | None:
        if cor_hex is not None and not HEX_COLOR_PATTERN.match(cor_hex):
            raise ValueError("Cor deve estar no formato hexadecimal #RRGGBB (ex: #1E3A8A)")
        return cor_hex


class InstitucionalResponse(InstitucionalBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(validation_alias="institucional_id", serialization_alias="id")

    @field_serializer("logotipo", "banner_hero", "imagem_sobre")
    def _serializar_url_midia(self, caminho_midia: str | None) -> str | None:
        return obter_url_publica(caminho_midia)


class InstitucionalUploadResponse(BaseModel):
    url: str
    warning: str | None = None


class MembroEquipePublicaResponse(BaseModel):
    nome: str
    cargo: str | None = None
    uf_oab: str | None = None
    numero_oab: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("cargo", mode="before")
    @classmethod
    def _extrair_nome_cargo(cls, cargo_ou_objeto: Any) -> str | None:
        if hasattr(cargo_ou_objeto, "nome_cargo"):
            return cargo_ou_objeto.nome_cargo
        return cast(str | None, cargo_ou_objeto)
