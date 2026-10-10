from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.cliente.model import Cliente
from app.solicitacao.schema import SolicitacaoCreate


class SolicitacaoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar_solicitacao_cliente(self, solicitacao: SolicitacaoCreate) -> Cliente:
        novo_cliente = Cliente(
            nome=solicitacao.nome,
            email=solicitacao.email,
            telefone=solicitacao.telefone,
            descricao=solicitacao.descricao,
            ultima_interacao=datetime.now(UTC),
            responsavel_id=None,
            etapa_id=1,  # Etapa inicial padrão ("Novo contato")
        )
        self.db.add(novo_cliente)
        self.db.commit()
        self.db.refresh(novo_cliente)
        return novo_cliente
