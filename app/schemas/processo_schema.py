from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class ProcessoBase(BaseModel):
    id: str # Nº do Processo
    titulo: str
    cliente: str
    status: str
    tribunal: str
    area: str
    responsavel: str
    prazo: str
    diasRestantes: Optional[int] = 15

class ProcessoCreate(ProcessoBase):
    pass

class ProcessoResponse(ProcessoBase):
    model_config = ConfigDict(from_attributes=True)

