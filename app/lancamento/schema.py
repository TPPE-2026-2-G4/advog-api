from pydantic import BaseModel, ConfigDict


class LancamentoBase(BaseModel):
    tipo: str
    titulo: str
    descricao: str | None = None
    valor: float
    data_vencimento: str
    data_pagamento: str | None = None
    categoria: str
    status: str | None = "Pendente"
    recorrente: bool | None = False


class LancamentoCreate(LancamentoBase):
    pass


class LancamentoUpdate(BaseModel):
    tipo: str | None = None
    titulo: str | None = None
    descricao: str | None = None
    valor: float | None = None
    data_vencimento: str | None = None
    data_pagamento: str | None = None
    categoria: str | None = None
    status: str | None = None
    recorrente: bool | None = None


class LancamentoStatusUpdate(BaseModel):
    status: str


class LancamentoResponse(LancamentoBase):
    lancamento_id: int

    model_config = ConfigDict(from_attributes=True)
