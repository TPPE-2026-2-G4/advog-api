from sqlalchemy import Column, DateTime, Integer, String

from app.config.database import Base


class Processo(Base):
    __tablename__ = "processos"

    processo_id = Column(Integer, primary_key=True, index=True)
    cnj = Column(String(20), unique=True, index=True)
    titulo_proc = Column(String(100))
    descricao_proc = Column(String(255), nullable=True)
    status = Column(String)
    tribunal = Column(String(100))
    area = Column(String(100))
    data_inicio = Column(DateTime, nullable=True)
    data_realizado = Column(DateTime, nullable=True)
    data_prazo = Column(DateTime, nullable=True)
    cliente_id = Column(Integer, nullable=True)
    responsavel_id = Column(Integer, nullable=True)
