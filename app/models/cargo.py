from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, Integer, String
from sqlalchemy.orm import Mapped, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.funcionario import Funcionario


class Cargo(Base):
    __tablename__ = "cargos"

    cargo_id = Column(Integer, primary_key=True, index=True)
    nome_cargo = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    permissao = Column(JSON, nullable=True)

    funcionarios: Mapped[list["Funcionario"]] = relationship("Funcionario", back_populates="cargo")
