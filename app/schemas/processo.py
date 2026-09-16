from pydantic import BaseModel, ConfigDict, Field

from app.models.processo import StatusProcesso


class ProcessoBase(BaseModel):
    id: str = Field(
        min_length=25,
        max_length=25,
        pattern=r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$",
        description="Número CNJ do processo",
    )
    titulo: str
    cliente: str
    status: StatusProcesso = StatusProcesso.EM_ANALISE
    tribunal: str
    area: str
    responsavel: str
    prazo: str = Field(max_length=10)
    diasRestantes: int | None = 15


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoUpdate(BaseModel):
    titulo: str | None = None
    cliente: str | None = None
    status: StatusProcesso | None = None
    tribunal: str | None = None
    area: str | None = None
    responsavel: str | None = None
    prazo: str | None = Field(default=None, max_length=10)
    diasRestantes: int | None = None


class ProcessoResponse(ProcessoBase):
    model_config = ConfigDict(from_attributes=True)
