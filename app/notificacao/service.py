import uuid

from sqlalchemy.orm import Session

from app.notificacao.model import Notificacao, TipoNotificacao
from app.notificacao.repository import NotificacaoRepository
from app.notificacao.schema import (
    ContagemNaoLidasResponse,
    NotificacaoCreate,
    NotificacaoRead,
)


class NotificacaoNaoEncontradaError(ValueError):
    pass


class NotificacaoAcessoNegadoError(ValueError):
    pass


class NotificacaoService:
    def __init__(self, db: Session):
        self.repository = NotificacaoRepository(db)

    def listar_notificacoes(
        self,
        funcionario_id: uuid.UUID,
        apenas_nao_lidas: bool = False,
        tipo: TipoNotificacao | None = None,
        limite: int = 50,
        offset: int = 0,
    ) -> list[NotificacaoRead]:
        notificacoes = self.repository.listar_por_usuario(
            funcionario_id=funcionario_id,
            apenas_nao_lidas=apenas_nao_lidas,
            tipo=tipo,
            limite=limite,
            offset=offset,
        )
        return [NotificacaoRead.model_validate(notificacao) for notificacao in notificacoes]

    def obter_contagem_nao_lidas(self, funcionario_id: uuid.UUID) -> ContagemNaoLidasResponse:
        total = self.repository.contar_nao_lidas(funcionario_id)
        return ContagemNaoLidasResponse(total_nao_lidas=total)

    def criar_notificacao(self, dados: NotificacaoCreate) -> NotificacaoRead:
        notificacao = Notificacao(**dados.model_dump())
        nova_notificacao = self.repository.criar(notificacao)
        return NotificacaoRead.model_validate(nova_notificacao)

    def marcar_como_lida(
        self, notificacao_id: uuid.UUID, funcionario_id: uuid.UUID
    ) -> NotificacaoRead:
        notificacao = self.repository.buscar_por_id(notificacao_id)
        if not notificacao:
            raise NotificacaoNaoEncontradaError("Notificação não encontrada.")

        if notificacao.funcionario_id != funcionario_id:
            raise NotificacaoAcessoNegadoError("Sem permissão para alterar esta notificação.")

        self.repository.marcar_como_lida(notificacao_id, funcionario_id)
        notificacao.lida = True
        return NotificacaoRead.model_validate(notificacao)

    def marcar_todas_como_lidas(self, funcionario_id: uuid.UUID) -> int:
        return self.repository.marcar_todas_como_lidas(funcionario_id)
