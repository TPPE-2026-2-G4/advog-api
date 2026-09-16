from sqlalchemy import Column, Integer, String

from app.config.database import Base


class Processo(Base):
    __tablename__ = "processos"

    processo_id = Column(Integer, primary_key=True, index=True)
    cnj = Column(String(20), unique=True, index=True)
    titulo = Column(String(100))
    descricao = Column(String(255), nullable=True)
    status = Column(String)
    tribunal = Column(String(100))
    area = Column(String(100))
    data_inicio = Column(String, nullable=True)
    data_realizado = Column(String, nullable=True)
    data_prazo = Column(String, nullable=True)
    cliente_id = Column(Integer, nullable=True)
