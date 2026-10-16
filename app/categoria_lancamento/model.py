from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.lancamento.model import Lancamento


class CategoriaLancamento(Base):
    __tablename__ = "categoria_lancamentos"

    categoria_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    nome_categoria: Mapped[str] = mapped_column(String(100), nullable=False)

    lancamentos: Mapped[list["Lancamento"]] = relationship(
        "Lancamento", back_populates="categoria_lancamento"
    )
