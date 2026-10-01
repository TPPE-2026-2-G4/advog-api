import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class StatusProcesso(enum.StrEnum):
    EM_ANALISE = "Em Análise"
    ATIVO = "Ativo"
    CONCLUIDO = "Concluído"
    ARQUIVADO = "Arquivado"


class Processo(Base):
    __tablename__ = "processos"

    processo_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    cnj: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[StatusProcesso] = mapped_column(
        Enum(
            StatusProcesso,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        default=StatusProcesso.EM_ANALISE,
    )
    tribunal: Mapped[str] = mapped_column(String(100), nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False)
    data_inicio: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data_realizado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data_prazo: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cliente_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.cliente_id"), nullable=True
    )
    responsavel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
