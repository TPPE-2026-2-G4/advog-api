import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SolicitacaoCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    telefone: str
    descricao: str = Field(..., min_length=10, max_length=2000)

    @field_validator("nome", mode="before")
    @classmethod
    def _limpar_nome(cls, valor: str) -> str:
        if isinstance(valor, str):
            return valor.strip()
        return valor

    @field_validator("telefone", mode="before")
    @classmethod
    def _limpar_telefone(cls, valor: str) -> str:
        if isinstance(valor, str):
            digitos = re.sub(r"\D", "", valor)
            if len(digitos) < 10 or len(digitos) > 11:
                raise ValueError("Telefone deve conter DDD + número (10 ou 11 dígitos).")
            return digitos
        return valor


class SolicitacaoResponse(BaseModel):
    cliente_id: int = Field(validation_alias="cliente_id")
    nome: str
    email: str
    telefone: str
    descricao: str
    etapa_id: int
    created_at: datetime | None = Field(default=None, validation_alias="ultima_interacao")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
