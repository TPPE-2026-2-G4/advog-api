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
        dias: int | None = Query(
            None, ge=1, description="Quantidade de dias recentes a considerar"
        ),
        valor_min: float | None = Query(
            None, ge=0, description="Valor mínimo do lançamento (inclusive)"
        ),
        valor_max: float | None = Query(
            None, ge=0, description="Valor máximo do lançamento (inclusive)"
        ),
        status: StatusLancamento | None = Query(
            None, description="Pendente, Realizado ou Atrasado"
        ),
        tipo: TipoLancamento | None = Query(None, description="e (entrada) ou s (saída)"),
        categoria_id: int | None = Query(None, description="Filtrar por categoria"),
        cliente_id: int | None = Query(None, description="Filtrar por cliente"),
    ):
        self.inicio = inicio
        self.fim = fim
        self.dias = dias
        self.valor_min = valor_min
        self.valor_max = valor_max
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


class PontoGrafico(BaseModel):
    data: date
    quantidade: int = 0
    total_entradas: float = 0.0
    total_saidas: float = 0.0
    saldo: float = 0.0


class LancamentoGrafico(BaseModel):
    inicio: date | None
    fim: date | None
    valor_min: float | None = None
    valor_max: float | None = None
    total_entradas: float = 0.0
    total_saidas: float = 0.0
    saldo: float = 0.0
    itens: list[PontoGrafico]
