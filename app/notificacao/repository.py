import uuid
from typing import cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.exc import IntegrityError
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
        funcionario_id: int,
        apenas_nao_lidas: bool = False,
        tipo: TipoNotificacao | None = None,
        limite: int = 50,
        offset: int = 0,
    ) -> list[Notificacao]:
        consulta = (
            select(Notificacao)
            .where(Notificacao.funcionario_id == funcionario_id)
            .order_by(Notificacao.criado_em.desc())
        )

        if apenas_nao_lidas:
            consulta = consulta.where(Notificacao.lida.is_(False))
        if tipo:
            consulta = consulta.where(Notificacao.tipo == tipo)

        consulta = consulta.offset(offset).limit(limite)
        return list(self.db.scalars(consulta))

    def contar_nao_lidas(self, funcionario_id: int) -> int:
        consulta = (
            select(func.count(Notificacao.id))
            .where(Notificacao.funcionario_id == funcionario_id)
            .where(Notificacao.lida.is_(False))
        )
        return self.db.scalar(consulta) or 0

    def criar(self, notificacao: Notificacao) -> Notificacao:
        self.db.add(notificacao)
        self.db.commit()
        self.db.refresh(notificacao)
        return notificacao

    def chaves_existentes(
        self, funcionario_ids: set[int], chaves: set[str]
    ) -> set[tuple[int, str]]:
        """Pares (funcionario_id, chave) que já foram avisados."""
        existentes: set[tuple[int, str]] = set()
        if not funcionario_ids or not chaves:
            return existentes
        lista = sorted(chaves)
        for inicio in range(0, len(lista), 500):
            consulta = select(Notificacao.funcionario_id, Notificacao.chave).where(
                Notificacao.funcionario_id.in_(funcionario_ids),
                Notificacao.chave.in_(lista[inicio : inicio + 500]),
            )
            existentes.update((fid, chave) for fid, chave in self.db.execute(consulta).all())
        return existentes

    def criar_varias(self, notificacoes: list[Notificacao]) -> int:
        """Grava as notificações de uma vez; se houver conflito de chave, grava uma a uma."""
        if not notificacoes:
            return 0
        try:
            self.db.add_all(notificacoes)
            self.db.commit()
            return len(notificacoes)
        except IntegrityError:
            self.db.rollback()
        criadas = 0
        for notificacao in notificacoes:
            try:
                self.db.add(notificacao)
                self.db.commit()
                criadas += 1
            except IntegrityError:
                self.db.rollback()  # outra execução já avisou esta pessoa sobre o mesmo fato
        return criadas

    def marcar_como_lida(self, notificacao_id: uuid.UUID, funcionario_id: int) -> bool:
        comando = (
            update(Notificacao)
            .where(
                Notificacao.id == notificacao_id,
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
