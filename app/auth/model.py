from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class TokenRecuperacaoSenha(Base):
    __tablename__ = "tokens_recuperacao_senha"

    token_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funcionario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("funcionarios.funcionario_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    funcionario = relationship("Funcionario")
