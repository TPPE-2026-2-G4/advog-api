import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.categoria_lancamento.model import CategoriaLancamento
from app.config.database import Base


class StatusLancamento(enum.StrEnum):
    PENDENTE = "Pendente"
    PAGO = "Pago"
    RECEBIDO = "Recebido"
    ATRASADO = "Atrasado"


class TipoLancamento(enum.StrEnum):
    ENTRADA = "e"
    SAIDA = "s"


class SituacaoLancamento(enum.StrEnum):
    PREVISTO = "Previsto"
    REALIZADO = "Realizado"
    ATRASADO = "Atrasado"


class Lancamento(Base):
    __tablename__ = "lancamentos"

    lancamento_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo: Mapped[TipoLancamento] = mapped_column(Enum(TipoLancamento), nullable=False)
    status: Mapped[StatusLancamento] = mapped_column(
        Enum(StatusLancamento), default=StatusLancamento.PENDENTE, nullable=False
    )
    data_vencimento: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_pagamento: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valor: Mapped[float] = mapped_column(Float, nullable=False)
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.cliente_id"), nullable=True
    )
    categoria_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categoria_lancamentos.categoria_id"), nullable=True
    )

    categoria_lancamento: Mapped[CategoriaLancamento | None] = relationship(
        "CategoriaLancamento", back_populates="lancamentos"
    )

    @property
    def situacao(self) -> SituacaoLancamento:
        if self.status in (StatusLancamento.PAGO, StatusLancamento.RECEBIDO):
            return SituacaoLancamento.REALIZADO
        if self.status == StatusLancamento.ATRASADO or self.data_vencimento < datetime.now():
            return SituacaoLancamento.ATRASADO
        return SituacaoLancamento.PREVISTO
