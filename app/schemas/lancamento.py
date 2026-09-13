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


class LancamentoResponse(LancamentoBase):
    lancamento_id: int

    model_config = ConfigDict(from_attributes=True)
