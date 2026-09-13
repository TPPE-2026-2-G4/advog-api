import enum

from sqlalchemy import CheckConstraint, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class StatusProcesso(enum.StrEnum):
    ATIVO = "Ativo"
    EM_ANALISE = "Em Análise"
    CONCLUIDO = "Concluído"
    PENDENTE = "Pendente"


class Processo(Base):
    __tablename__ = "processos"

    id: Mapped[str] = mapped_column(String(25), primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    cliente: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[StatusProcesso] = mapped_column(
        Enum(StatusProcesso), nullable=False, default=StatusProcesso.EM_ANALISE
    )
    tribunal: Mapped[str] = mapped_column(String(20), nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False)
    responsavel: Mapped[str] = mapped_column(String(100), nullable=False)
    prazo: Mapped[str] = mapped_column(String(10), nullable=False)
    diasRestantes: Mapped[int] = mapped_column(Integer, default=15)

    __table_args__ = (
        CheckConstraint("length(id) = 25", name="ck_id_tamanho"),
        CheckConstraint("length(prazo) = 10", name="ck_prazo_tamanho"),
    )
