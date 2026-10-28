from datetime import date, datetime

from fastapi import Query
from fastapi.params import Param
from pydantic import BaseModel, ConfigDict, Field

from app.lancamento.model import StatusLancamento, TipoLancamento


class LancamentoBase(BaseModel):
    titulo: str = Field(min_length=1, max_length=100)
    descricao: str = Field(min_length=1, max_length=255)
    tipo: TipoLancamento
    data_vencimento: datetime
    valor: float = Field(gt=0)
    cliente_id: int | None = None
    categoria_id: int


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
        self.inicio = None if isinstance(inicio, Param) else inicio
        self.fim = None if isinstance(fim, Param) else fim
        self.dias = None if isinstance(dias, Param) else dias
        self.valor_min = None if isinstance(valor_min, Param) else valor_min
        self.valor_max = None if isinstance(valor_max, Param) else valor_max
        self.status = None if isinstance(status, Param) else status
        self.tipo = None if isinstance(tipo, Param) else tipo
        self.categoria_id = None if isinstance(categoria_id, Param) else categoria_id
        self.cliente_id = None if isinstance(cliente_id, Param) else cliente_id


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


class LancamentoCalendarioResponse(BaseModel):
    lancamento_id: int
    titulo: str
    descricao: str
    tipo: TipoLancamento
    status: StatusLancamento
    valor: float
    data_vencimento: datetime
    data_pagamento: datetime | None = None
    categoria_id: int
    cliente_id: int | None = None
    google_calendar_url: str
    outlook_calendar_url: str

    model_config = ConfigDict(from_attributes=True)


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
