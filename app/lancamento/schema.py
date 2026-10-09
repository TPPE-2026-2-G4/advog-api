from datetime import date, datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.lancamento.model import SituacaoLancamento, StatusLancamento, TipoLancamento


class LancamentoBase(BaseModel):
    titulo: str = Field(min_length=1, max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    tipo: TipoLancamento
    status: StatusLancamento = StatusLancamento.PENDENTE
    data_vencimento: datetime
    data_pagamento: datetime | None = None
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
    data_pagamento: datetime | None = None
    valor: float | None = Field(default=None, gt=0)
    cliente_id: int | None = None
    categoria_id: int | None = None


class LancamentoStatusUpdate(BaseModel):
    status: StatusLancamento


class LancamentoResponse(LancamentoBase):
    lancamento_id: int
    situacao: SituacaoLancamento

    model_config = ConfigDict(from_attributes=True)


class LancamentoFilter:
    def __init__(
        self,
        inicio: date | None = Query(None, description="Vencimento a partir de (inclusive)"),
        fim: date | None = Query(None, description="Vencimento até (inclusive)"),
        situacao: SituacaoLancamento | None = Query(
            None, description="Previsto, Realizado ou Atrasado"
        ),
        tipo: TipoLancamento | None = Query(None, description="e (entrada) ou s (saída)"),
        categoria_id: int | None = Query(None, description="Filtrar por categoria"),
        cliente_id: int | None = Query(None, description="Filtrar por cliente"),
    ):
        self.inicio = inicio
        self.fim = fim
        self.situacao = situacao
        self.tipo = tipo
        self.categoria_id = categoria_id
        self.cliente_id = cliente_id


class ResumoSituacao(BaseModel):
    quantidade: int = 0
    total_entradas: float = 0.0
    total_saidas: float = 0.0


class LancamentoResumo(BaseModel):
    inicio: date | None
    fim: date | None
    previsto: ResumoSituacao
    realizado: ResumoSituacao
    atrasado: ResumoSituacao
