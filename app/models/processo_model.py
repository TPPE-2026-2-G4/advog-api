from sqlalchemy import Column, Integer, String

from app.config.database import Base


class Processo(Base):
    __tablename__ = "processos"

    id = Column(String, primary_key=True, index=True)  # Corresponde ao Nº do Processo no frontend
    titulo = Column(String)
    cliente = Column(String)
    status = Column(String)
    tribunal = Column(String)
    area = Column(String)
    responsavel = Column(String)
    prazo = Column(String)
    diasRestantes = Column(Integer, default=15)
