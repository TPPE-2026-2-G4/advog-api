from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Atuacao(Base):
    __tablename__ = "atuacoes"

    atuacao_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    exibicao_institucional: Mapped[bool] = mapped_column(
        "exibicaoInstitucional", Boolean, nullable=False, default=True
    )

    @property
    def titulo(self) -> str:
        return self.nome
