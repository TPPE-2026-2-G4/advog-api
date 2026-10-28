from datetime import datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field

ETAPA_INICIAL_ID = 1


class ClienteBase(BaseModel):
    nome: str
    telefone: str = Field(max_length=16)
    email: EmailStr
    area_interesse: str | None = None
    descricao: str | None = None
    documento: str | None = None
    responsavel_id: int | None = None


class ClienteCreate(ClienteBase):
    nome: str = Field(min_length=1, max_length=100)
    descricao: str | None = Field(default=None, max_length=2000)
    documento: str | None = Field(default=None, max_length=20)
    ultima_interacao: datetime | None = None
    etapa_id: int = ETAPA_INICIAL_ID


class ClienteUpdate(ClienteBase):
    ultima_interacao: datetime
    etapa_id: int


class ClienteResponse(ClienteBase):
    cliente_id: int
    ultima_interacao: datetime
    etapa_id: int

    model_config = ConfigDict(from_attributes=True)


class ClienteFilter:
    def __init__(
        self,
        busca: str | None = Query(None, description="Buscar por nome ou email"),
        responsavel_id: int | None = Query(None, description="Filtrar por responsável"),
        etapa_id: int | None = Query(None, description="Filtrar por etapa"),
    ):
        self.busca = busca
        self.responsavel_id = responsavel_id
        self.etapa_id = etapa_id
