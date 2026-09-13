from pydantic import BaseModel, ConfigDict
from typing import Optional

class LancamentoBase(BaseModel):
    tipo: str
    titulo: str
    descricao: Optional[str] = None
    valor: float
    data: str
    categoria: str
    status: Optional[str] = "Pendente"
    recorrente: Optional[bool] = False

class LancamentoCreate(LancamentoBase):
    pass

class LancamentoResponse(LancamentoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
