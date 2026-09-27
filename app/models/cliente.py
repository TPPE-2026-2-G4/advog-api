from sqlalchemy import Column, DateTime, Integer, String

from app.config.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    cliente_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), unique=True, index=True, nullable=True)
    telefone = Column(String(16), nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=True)
    area_interesse = Column(String(50), nullable=True)
    ultima_interacao = Column(DateTime, nullable=True)
    responsavel_id = Column(Integer, nullable=True)
    etapa_id = Column(Integer, nullable=True)
