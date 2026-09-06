from pydantic import BaseModel, ConfigDict


class ProcessoBase(BaseModel):
    id: str  # Nº do Processo
    titulo: str
    cliente: str
    status: str
    tribunal: str
    area: str
    responsavel: str
    prazo: str
    diasRestantes: int | None = 15


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoResponse(ProcessoBase):
    model_config = ConfigDict(from_attributes=True)
