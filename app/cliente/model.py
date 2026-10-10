from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    cliente_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    telefone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    documento: Mapped[str] = mapped_column(String(20), nullable=True)
    etapa_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    responsavel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ultima_interacao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    area_interesse: Mapped[str | None] = mapped_column(String(50), nullable=True)
