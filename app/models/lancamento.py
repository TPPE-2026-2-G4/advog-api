from sqlalchemy import Column, Integer, String, Float, Boolean
from app.config.database import Base

class Lancamento(Base):
    __tablename__ = "lancamentos"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)
    titulo = Column(String)
    descricao = Column(String, nullable=True)
    valor = Column(Float)
    data = Column(String)
    categoria = Column(String)
    status = Column(String, default="Pendente")
    recorrente = Column(Boolean, default=False)
