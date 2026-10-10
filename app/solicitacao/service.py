import logging

from sqlalchemy.orm import Session

from app.cliente.model import Cliente
from app.solicitacao.repository import SolicitacaoRepository
from app.solicitacao.schema import SolicitacaoCreate

logger = logging.getLogger(__name__)


class SolicitacaoService:
    def __init__(self, db: Session):
        self.db = db
        self.solicitacao_repo = SolicitacaoRepository(db)

    def registrar_solicitacao(self, solicitacao: SolicitacaoCreate) -> Cliente:
        logger.info("Iniciando registro de nova solicitação de serviço.")

        nova_solicitacao = self.solicitacao_repo.criar_solicitacao_cliente(solicitacao)

        logger.info(f"Solicitação criada com sucesso. ID: {nova_solicitacao.id}")
        return nova_solicitacao
