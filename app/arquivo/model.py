from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Arquivo(Base):
    __tablename__ = "arquivos"

    arquivo_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    bucket_link: Mapped[str] = mapped_column(String(500), nullable=False)
    origem: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    data_upload: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    funcionario_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "funcionarios.funcionario_id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_arquivos_funcionario_id",
        ),
        nullable=True,
    )
