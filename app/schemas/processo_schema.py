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


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoResponse(ProcessoBase):
    processo_id: int

    model_config = ConfigDict(from_attributes=True)
