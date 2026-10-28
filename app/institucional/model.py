from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.arquivo.model import Arquivo
from app.config.database import Base


class Institucional(Base):
    __tablename__ = "institucional"

    institucional_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nome_escritorio: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Escritório de Advocacia"
    )
    descricao: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    sobre_escritorio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    telefone: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    endereco: Mapped[str] = mapped_column(Text, nullable=False, default="")

    cor_primaria: Mapped[str] = mapped_column(String(7), nullable=False, default="#1B2A4A")
    cor_secundaria: Mapped[str] = mapped_column(String(7), nullable=False, default="#B79A63")

    imagem_logotipo: Mapped[int] = mapped_column(
        Integer, ForeignKey("arquivos.arquivo_id"), nullable=False
    )
    banner_hero: Mapped[int] = mapped_column(
        Integer, ForeignKey("arquivos.arquivo_id"), nullable=False
    )
    imagem_sobre_escritorio: Mapped[int] = mapped_column(
        Integer, ForeignKey("arquivos.arquivo_id"), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    arquivo_logotipo: Mapped[Arquivo] = relationship(Arquivo, foreign_keys=[imagem_logotipo])
    arquivo_banner: Mapped[Arquivo] = relationship(Arquivo, foreign_keys=[banner_hero])
    arquivo_sobre: Mapped[Arquivo] = relationship(Arquivo, foreign_keys=[imagem_sobre_escritorio])

    __table_args__ = (CheckConstraint("institucional_id = 1", name="ck_institucional_singleton"),)

    @property
    def link_logotipo(self) -> str:
        return self.arquivo_logotipo.bucket_link

    @property
    def link_banner(self) -> str:
        return self.arquivo_banner.bucket_link

    @property
    def link_imagem_sobre(self) -> str:
        return self.arquivo_sobre.bucket_link
