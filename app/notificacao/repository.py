from typing import cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session

from app.notificacao.model import Notificacao, TipoNotificacao


class NotificacaoRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_id(self, notificacao_id: int) -> Notificacao | None:
        consulta = select(Notificacao).where(Notificacao.notificacao_id == notificacao_id)
        return self.db.scalars(consulta).first()

    def listar_por_funcionario(
        self,
        funcionario_id: int,
        apenas_nao_lidas: bool = False,
        tipo: TipoNotificacao | None = None,
        limite: int = 50,
        offset: int = 0,
    ) -> list[Notificacao]:
        consulta = (
            select(Notificacao)
            .where(Notificacao.funcionario_id == funcionario_id)
            .order_by(Notificacao.created_at.desc())
        )

        if apenas_nao_lidas:
            consulta = consulta.where(Notificacao.lida.is_(False))
        if tipo:
            consulta = consulta.where(Notificacao.tipo == tipo)

        consulta = consulta.offset(offset).limit(limite)
        return list(self.db.scalars(consulta))

    def contar_nao_lidas(self, funcionario_id: int) -> int:
        consulta = (
            select(func.count(Notificacao.notificacao_id))
            .where(Notificacao.funcionario_id == funcionario_id)
            .where(Notificacao.lida.is_(False))
        )
        return self.db.scalar(consulta) or 0

    def criar(self, notificacao: Notificacao) -> Notificacao:
        self.db.add(notificacao)
        self.db.commit()
        self.db.refresh(notificacao)
        return notificacao

    def marcar_como_lida(self, notificacao_id: int, funcionario_id: int) -> bool:
        comando = (
            update(Notificacao)
            .where(
                Notificacao.notificacao_id == notificacao_id,
                Notificacao.funcionario_id == funcionario_id,
            )
            .values(lida=True)
        )
        resultado = cast(CursorResult, self.db.execute(comando))
        self.db.commit()
        return (resultado.rowcount or 0) > 0

    def marcar_todas_como_lidas(self, funcionario_id: int) -> int:
        comando = (
            update(Notificacao)
            .where(
                Notificacao.funcionario_id == funcionario_id,
                Notificacao.lida.is_(False),
            )
            .values(lida=True)
        )
        resultado = cast(CursorResult, self.db.execute(comando))
        self.db.commit()
        return resultado.rowcount or 0
