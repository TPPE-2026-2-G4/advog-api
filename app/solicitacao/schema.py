import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SolicitacaoCreate(BaseModel):
    nome: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Nome completo do cliente",
    )
    email: EmailStr = Field(..., description="E-mail de contato do cliente")
    telefone: str = Field(..., description="Telefone de contato com DDD (ex: (61) 99999-9999)")
    descricao: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Descrição detalhada da demanda ou situação jurídica",
    )

    @field_validator("nome", mode="before")
    @classmethod
    def sanitizar_nome(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("telefone")
    @classmethod
    def validar_e_formatar_telefone(cls, value: str) -> str:
        digitos = re.sub(r"\D", "", value)
        if len(digitos) not in (10, 11):
            raise ValueError("O telefone deve conter o DDD e ter 10 ou 11 dígitos numéricos.")
        return value


class SolicitacaoResponse(BaseModel):
    id: int = Field(..., validation_alias="cliente_id")
    nome: str
    email: EmailStr
    telefone: str
    descricao: str
    status: str = Field(default="Novo contato")
    criado_em: datetime = Field(..., validation_alias="ultima_interacao")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
