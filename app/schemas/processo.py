from fastapi import Query
from pydantic import BaseModel, ConfigDict


class ProcessoBase(BaseModel):
    cnj: str | None = None
    titulo: str
    descricao: str | None = None
    status: str
    tribunal: str
    area: str
    data_inicio: str | None = None
    data_realizado: str | None = None
    data_prazo: str | None = None
    cliente_id: int | None = None
    responsavel_id: int | None = None


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoResponse(ProcessoBase):
    processo_id: int

    model_config = ConfigDict(from_attributes=True)


class ProcessoFilter:
    def __init__(
        self,
        processo_id: int | None = Query(None, description="Filtrar por ID do processo"),
        cnj: str | None = Query(None, description="Filtrar por CNJ"),
        titulo: str | None = Query(None, description="Filtrar por título"),
        descricao: str | None = Query(None, description="Filtrar por descrição"),
        status: str | None = Query(None, description="Filtrar por status"),
        tribunal: str | None = Query(None, description="Filtrar por tribunal"),
        area: str | None = Query(None, description="Filtrar por área"),
        cliente_id: int | None = Query(None, description="Filtrar por ID do cliente"),
        responsavel_id: int | None = Query(None, description="Filtrar por ID do responsável"),
    ):
        self.processo_id = processo_id
        self.cnj = cnj
        self.titulo = titulo
        self.descricao = descricao
        self.status = status
        self.tribunal = tribunal
        self.area = area
        self.cliente_id = cliente_id
        self.responsavel_id = responsavel_id
