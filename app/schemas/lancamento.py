from pydantic import BaseModel, ConfigDict


class LancamentoBase(BaseModel):
    tipo: str
    titulo: str
    descricao: str | None = None
    valor: float
    data: str
    categoria: str
    status: str | None = "Pendente"
    recorrente: bool | None = False


class LancamentoCreate(LancamentoBase):
    pass


class LancamentoResponse(LancamentoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
