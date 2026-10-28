from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.atividade_funcionario.model import AtividadeFuncionario
from app.config.database import Base
from app.etapa_kanban.model import EtapaKanban
from app.funcionario.model import Funcionario


class Atividade(Base):
    __tablename__ = "atividades"

    atividade_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_prazo: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_realizado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    etapa_id: Mapped[int] = mapped_column(
        ForeignKey("etapas_kanban.etapa_id"), nullable=False, index=True
    )
    processo_id: Mapped[int | None] = mapped_column(
        ForeignKey("processos.processo_id", ondelete="SET NULL"), nullable=True, index=True
    )

    etapa: Mapped[EtapaKanban] = relationship(EtapaKanban, back_populates="atividades_vinculadas")
    funcionarios: Mapped[list[Funcionario]] = relationship(
        Funcionario,
        secondary=AtividadeFuncionario.__table__,
        order_by=Funcionario.funcionario_id,
    )
