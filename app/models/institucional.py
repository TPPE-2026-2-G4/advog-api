from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Institucional(Base):
    __tablename__ = "institucional"

    institucional_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nome_escritorio: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Escritório de Advocacia"
    )
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sobre_escritorio: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    endereco: Mapped[str | None] = mapped_column(Text, nullable=True)

    cor_primaria: Mapped[str] = mapped_column(String(7), nullable=False, default="#1B2A4A")
    cor_secundaria: Mapped[str] = mapped_column(String(7), nullable=False, default="#B79A63")

    logotipo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner_hero: Mapped[str | None] = mapped_column(String(255), nullable=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.timetz, onupdate=datetime.timetz
    )
