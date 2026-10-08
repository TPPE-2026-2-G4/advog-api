from datetime import date, datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict


class ProcessoBase(BaseModel):
    cnj: str | None = None
    titulo_proc: str
    descricao_proc: str | None = None
    status: str
    tribunal: str
    area: str
    data_inicio: datetime | None = None
    data_realizado: datetime | None = None
    data_prazo: datetime | None = None
    cliente_id: int | None = None
    responsavel_id: int | None = None


class ProcessoCreate(ProcessoBase):
    pass


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
        titulo_proc: str | None = Query(None, description="Filtrar por título do processo"),
        descricao_proc: str | None = Query(None, description="Filtrar por descrição do processo"),
        status: str | None = Query(None, description="Filtrar por status"),
        tribunal: str | None = Query(None, description="Filtrar por tribunal"),
        area: str | None = Query(None, description="Filtrar por área"),
        cliente_id: int | None = Query(None, description="Filtrar por ID do cliente"),
        responsavel_id: int | None = Query(None, description="Filtrar por ID do responsável"),
        busca: str | None = Query(None, description="Buscar por número CNJ ou título do processo"),
        prazo_inicio: date | None = Query(None, description="Prazo a partir de (inclusive)"),
        prazo_fim: date | None = Query(None, description="Prazo até (inclusive)"),
        page: int = Query(1, ge=1, description="Página a ser retornada"),
        page_size: int = Query(10, ge=1, le=100, description="Quantidade de itens por página"),
    ):
        self.processo_id = processo_id
        self.cnj = cnj
        self.titulo_proc = titulo_proc
        self.descricao_proc = descricao_proc
        self.status = status
        self.tribunal = tribunal
        self.area = area
        self.cliente_id = cliente_id
        self.responsavel_id = responsavel_id
        self.busca = busca
        self.prazo_inicio = prazo_inicio
        self.prazo_fim = prazo_fim
        self.page = page
        self.page_size = page_size
