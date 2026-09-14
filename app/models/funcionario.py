import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.cargo import Cargo


class StatusFuncionario(enum.StrEnum):
    PENDENTE = "Pendente"
    ATIVO = "Ativo"
    INATIVO = "Inativo"


class Funcionario(Base):
    __tablename__ = "funcionarios"

    funcionario_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uf_oab: Mapped[str | None] = mapped_column(String(2), nullable=True)
    numero_oab: Mapped[str | None] = mapped_column(String(5), nullable=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    senha_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[StatusFuncionario] = mapped_column(
        Enum(StatusFuncionario), nullable=False, default=StatusFuncionario.PENDENTE
    )
    exibicaoInstitucional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    cargo_id: Mapped[int] = mapped_column(Integer, ForeignKey("cargos.cargo_id"), nullable=False)
    cargo: Mapped["Cargo"] = relationship("Cargo", back_populates="funcionarios")

    __table_args__ = (
        CheckConstraint("uf_oab IS NULL OR length(uf_oab) = 2", name="ck_uf_oab_tamanho"),
        CheckConstraint(
            "numero_oab IS NULL OR length(numero_oab) = 5", name="ck_numero_oab_tamanho"
        ),
    )
