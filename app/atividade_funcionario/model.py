from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class AtividadeFuncionario(Base):
    __tablename__ = "atividade_funcionario"

    funcionario_id: Mapped[int] = mapped_column(
        ForeignKey("funcionarios.funcionario_id"), primary_key=True
    )
    atividade_id: Mapped[int] = mapped_column(
        ForeignKey("atividade.atividade_id"), primary_key=True
    )
