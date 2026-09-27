from datetime import datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, EmailStr


class ClienteBase(BaseModel):
    nome: str
    cpf: str | None = None
    telefone: str | None = None
    email: EmailStr | None = None
    area_interesse: str | None = None
    ultima_interacao: datetime | None = None
    responsavel_id: int | None = None
    etapa_id: int | None = None


class ClienteCreate(ClienteBase):
    pass


class ClienteResponse(ClienteBase):
    cliente_id: int

    model_config = ConfigDict(from_attributes=True)


class ClienteFilter:
    def __init__(
        self,
        busca: str | None = Query(None, description="Buscar por nome, email ou cpf"),
        responsavel_id: int | None = Query(None, description="Filtrar por responsável"),
        etapa_id: int | None = Query(None, description="Filtrar por etapa"),
    ):
        self.busca = busca
        self.responsavel_id = responsavel_id
        self.etapa_id = etapa_id
