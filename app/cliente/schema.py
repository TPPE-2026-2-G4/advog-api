from datetime import datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, EmailStr


class ClienteBase(BaseModel):
    nome: str
    telefone: str | None = None
    email: EmailStr
    area_interesse: str | None = None
    descricao: str | None = None
    ultima_interacao: datetime
    responsavel_id: int | None = None
    etapa_id: int


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    pass


class ClienteResponse(ClienteBase):
    cliente_id: int

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
