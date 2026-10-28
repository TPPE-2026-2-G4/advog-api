from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class EtapaCliente(Base):
    __tablename__ = "etapas_cliente"

    etapa_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_etapa: Mapped[str] = mapped_column(String(100), nullable=False)
