from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class AtividadeFuncionario(Base):
    __tablename__ = "atividades_funcionarios"

    funcionario_id: Mapped[int] = mapped_column(
        ForeignKey("funcionarios.funcionario_id", ondelete="CASCADE"), primary_key=True
    )
    atividade_id: Mapped[int] = mapped_column(
        ForeignKey("atividades.atividade_id", ondelete="CASCADE"), primary_key=True
    )
