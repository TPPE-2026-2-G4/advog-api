from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.funcionario import Funcionario


class Cargo(Base):
    __tablename__ = "cargos"

    cargo_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    nome_cargo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permissao: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=False)

    funcionarios: Mapped[list["Funcionario"]] = relationship("Funcionario", back_populates="cargo")
