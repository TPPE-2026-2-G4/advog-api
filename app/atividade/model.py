from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Atividade(Base):
    __tablename__ = "atividade"

    atividade_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=False)
    data_inicio: Mapped[datetime | None] = mapped_column(DateTime, nullable=False)
    data_prazo: Mapped[datetime | None] = mapped_column(DateTime, nullable=False)
    data_realizado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    etapa_id: Mapped[int] = mapped_column(ForeignKey("etapa_kanban.etapa_id"), nullable=False)
    processo_id: Mapped[int | None] = mapped_column(
        ForeignKey("processos.processo_id"), nullable=True
    )
