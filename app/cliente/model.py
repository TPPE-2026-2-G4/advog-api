from sqlalchemy import Column, DateTime, Integer, String, Text

from app.config.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    cliente_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    telefone = Column(String(16), nullable=False)
    email = Column(String(100), index=True, nullable=False)
    area_interesse = Column(String(50), nullable=True)
    descricao = Column(Text, nullable=True)
    ultima_interacao = Column(DateTime, nullable=False)
    responsavel_id = Column(Integer, nullable=True)
    etapa_id = Column(Integer, nullable=False)
