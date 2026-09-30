import enum

from sqlalchemy import Boolean, Column, Float, Integer, String

from app.config.database import Base


class StatusLancamento(enum.StrEnum):
    PENDENTE = "Pendente"
    PAGO = "Pago"
    RECEBIDO = "Recebido"
    ATRASADO = "Atrasado"


class Lancamento(Base):
    __tablename__ = "lancamentos"

    lancamento_id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)
    titulo = Column(String)
    descricao = Column(String, nullable=True)
    valor = Column(Float)
    data_vencimento = Column(String)
    data_pagamento = Column(String, nullable=True)
    categoria = Column(String)
    status = Column(String, default=StatusLancamento.PENDENTE)
    recorrente = Column(Boolean, default=False)
