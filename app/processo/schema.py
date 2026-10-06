from datetime import datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.processo.model import StatusProcesso


class ProcessoBase(BaseModel):
    cnj: str = Field(max_length=20)
    titulo: str = Field(max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    status: StatusProcesso = StatusProcesso.EM_ANALISE
    tribunal: str = Field(max_length=100)
    area: str = Field(max_length=100)
    data_inicio: datetime | None = None
    data_realizado: datetime | None = None
    data_prazo: datetime | None = None
    cliente_id: int | None = None
    funcionario_id: int | None = None


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoUpdate(BaseModel):
    cnj: str | None = Field(default=None, max_length=20)
    titulo: str | None = Field(default=None, max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    status: StatusProcesso | None = None
    tribunal: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=100)
    data_inicio: datetime | None = None
    data_realizado: datetime | None = None
    data_prazo: datetime | None = None
    cliente_id: int | None = None
    funcionario_id: int | None = None


class ProcessoResponse(ProcessoBase):
    processo_id: int

    model_config = ConfigDict(from_attributes=True)


class ProcessoFilter:
    def __init__(
        self,
        processo_id: int | None = Query(None, description="Filtrar por ID do processo"),
        cnj: str | None = Query(None, description="Filtrar por CNJ"),
        titulo: str | None = Query(None, description="Filtrar por título do processo"),
        descricao: str | None = Query(None, description="Filtrar por descrição do processo"),
        status: StatusProcesso | None = Query(None, description="Filtrar por status"),
        tribunal: str | None = Query(None, description="Filtrar por tribunal"),
        area: str | None = Query(None, description="Filtrar por área"),
        cliente_id: int | None = Query(None, description="Filtrar por ID do cliente"),
        funcionario_id: int | None = Query(None, description="Filtrar por ID do funcionário"),
    ):
        self.processo_id = processo_id
        self.cnj = cnj
        self.titulo = titulo
        self.descricao = descricao
        self.status = status
        self.tribunal = tribunal
        self.area = area
        self.cliente_id = cliente_id
        self.funcionario_id = funcionario_id
