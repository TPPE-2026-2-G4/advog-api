import uuid
from typing import cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session

from app.notificacao.model import Notificacao, TipoNotificacao


class NotificacaoRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_id(self, notificacao_id: uuid.UUID) -> Notificacao | None:
        consulta = select(Notificacao).where(Notificacao.id == notificacao_id)
        return self.db.scalars(consulta).first()

    def listar_por_usuario(
        self,
        usuario_id: uuid.UUID,
        apenas_nao_lidas: bool = False,
        tipo: TipoNotificacao | None = None,
        limite: int = 50,
        offset: int = 0,
    ) -> list[Notificacao]:
        consulta = (
            select(Notificacao)
            .where(Notificacao.usuario_id == usuario_id)
            .order_by(Notificacao.criado_em.desc())
        )

        if apenas_nao_lidas:
            consulta = consulta.where(Notificacao.lida.is_(False))
        if tipo:
            consulta = consulta.where(Notificacao.tipo == tipo)

        consulta = consulta.offset(offset).limit(limite)
        return list(self.db.scalars(consulta))

    def contar_nao_lidas(self, usuario_id: uuid.UUID) -> int:
        consulta = (
            select(func.count(Notificacao.id))
            .where(Notificacao.usuario_id == usuario_id)
            .where(Notificacao.lida.is_(False))
        )
        return self.db.scalar(consulta) or 0

    def criar(self, notificacao: Notificacao) -> Notificacao:
        self.db.add(notificacao)
        self.db.commit()
        self.db.refresh(notificacao)
        return notificacao

    def marcar_como_lida(self, notificacao_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        comando = (
            update(Notificacao)
            .where(
                Notificacao.id == notificacao_id,
                Notificacao.usuario_id == usuario_id,
            )
            .values(lida=True)
        )
        resultado = cast(CursorResult, self.db.execute(comando))
        self.db.commit()
        return (resultado.rowcount or 0) > 0

    def marcar_todas_como_lidas(self, usuario_id: uuid.UUID) -> int:
        comando = (
            update(Notificacao)
            .where(
                Notificacao.usuario_id == usuario_id,
                Notificacao.lida.is_(False),
            )
            .values(lida=True)
        )
        resultado = cast(CursorResult, self.db.execute(comando))
        self.db.commit()
        return resultado.rowcount or 0
