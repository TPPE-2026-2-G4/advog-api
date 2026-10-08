from datetime import date, datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.processo.model import StatusProcesso


class ProcessoBase(BaseModel):
    cnj: str = Field(max_length=25)
    titulo: str = Field(max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    status: StatusProcesso = StatusProcesso.EM_ANALISE
    tribunal: str = Field(max_length=100)
    area: str = Field(max_length=100)
    data_inicio: datetime | None = None
    data_realizado: datetime | None = None
    data_prazo: datetime | None = None
    cliente_id: int
    funcionario_id: int | None = None


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoUpdate(BaseModel):
    cnj: str | None = Field(default=None, max_length=25)
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


class ProcessoPaginadoResponse(BaseModel):
    itens: list[ProcessoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


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
        busca: str | None = Query(None, description="Buscar por número CNJ, título ou nome do cliente"),
        prazo_inicio: date | None = Query(None, description="Prazo a partir de (inclusive)"),
        prazo_fim: date | None = Query(None, description="Prazo até (inclusive)"),
        page: int = Query(1, ge=1, description="Página a ser retornada"),
        page_size: int = Query(10, ge=1, le=100, description="Quantidade de itens por página"),
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
        self.busca = busca
        self.prazo_inicio = prazo_inicio
        self.prazo_fim = prazo_fim
        self.page = page
        self.page_size = page_size
