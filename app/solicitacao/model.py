from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.config.database import Base


class SolicitacaoModel(Base):
    __tablename__ = "solicitacoes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    telefone = Column(String(20), nullable=False)
    descricao = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="PENDENTE", index=True)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
