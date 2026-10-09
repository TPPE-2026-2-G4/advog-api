from datetime import date, datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.lancamento.model import StatusLancamento, TipoLancamento


class LancamentoBase(BaseModel):
    titulo: str = Field(min_length=1, max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    tipo: TipoLancamento
    data_vencimento: datetime
    valor: float = Field(gt=0)
    cliente_id: int | None = None
    categoria_id: int | None = None


class LancamentoCreate(LancamentoBase):
    pass


class LancamentoUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    tipo: TipoLancamento | None = None
    data_vencimento: datetime | None = None
    valor: float | None = Field(default=None, gt=0)
    cliente_id: int | None = None
    categoria_id: int | None = None


class LancamentoResponse(LancamentoBase):
    lancamento_id: int
    status: StatusLancamento
    data_pagamento: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LancamentoPaginadoResponse(BaseModel):
    itens: list[LancamentoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LancamentoFilter:
    def __init__(
        self,
        inicio: date | None = Query(None, description="Vencimento a partir de (inclusive)"),
        fim: date | None = Query(None, description="Vencimento até (inclusive)"),
        status: StatusLancamento | None = Query(
            None, description="Pendente, Realizado ou Atrasado"
        ),
        tipo: TipoLancamento | None = Query(None, description="e (entrada) ou s (saída)"),
        categoria_id: int | None = Query(None, description="Filtrar por categoria"),
        cliente_id: int | None = Query(None, description="Filtrar por cliente"),
    ):
        self.inicio = inicio
        self.fim = fim
        self.status = status
        self.tipo = tipo
        self.categoria_id = categoria_id
        self.cliente_id = cliente_id


class ResumoStatus(BaseModel):
    quantidade: int = 0
    total_entradas: float = 0.0
    total_saidas: float = 0.0


class LancamentoResumo(BaseModel):
    inicio: date | None
    fim: date | None
    pendente: ResumoStatus
    realizado: ResumoStatus
    atrasado: ResumoStatus
