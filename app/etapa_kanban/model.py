from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.atividade.model import Atividade


class EtapaKanban(Base):
    __tablename__ = "etapas_kanban"

    etapa_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    atividades_vinculadas: Mapped[list["Atividade"]] = relationship(
        "Atividade", back_populates="etapa"
    )
