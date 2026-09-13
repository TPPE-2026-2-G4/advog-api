from pydantic import BaseModel, ConfigDict, Field

from app.models.processo import StatusProcesso


class ProcessoBase(BaseModel):
    id: str = Field(max_length=25)
    titulo: str
    cliente: str
    status: StatusProcesso
    tribunal: str
    area: str
    responsavel: str
    prazo: str = Field(max_length=10)
    diasRestantes: int | None = 15


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoResponse(ProcessoBase):
    model_config = ConfigDict(from_attributes=True)
