from datetime import date, datetime, time, timedelta

from sqlalchemy import Row, func, update
from sqlalchemy.orm import Query, Session

from app.categoria_lancamento.model import CategoriaLancamento
from app.cliente.model import Cliente
from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento


class LancamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def marcar_atrasados(self, hoje: date) -> None:
        self.db.execute(
            update(Lancamento)
            .where(
                Lancamento.status == StatusLancamento.PENDENTE,
                Lancamento.data_vencimento < datetime.combine(hoje, time.min),
            )
            .values(status=StatusLancamento.ATRASADO)
        )
        self.db.commit()

    def _filtrar(
        self,
        inicio: date | None,
        fim: date | None,
        status: StatusLancamento | None,
        tipo: TipoLancamento | None,
        categoria_id: int | None,
        cliente_id: int | None,
    ) -> Query:
        query = self.db.query(Lancamento)
        if inicio is not None:
            query = query.filter(Lancamento.data_vencimento >= datetime.combine(inicio, time.min))
        if fim is not None:
            limite = datetime.combine(fim + timedelta(days=1), time.min)
            query = query.filter(Lancamento.data_vencimento < limite)
        if status is not None:
            query = query.filter(Lancamento.status == status)
        if tipo is not None:
            query = query.filter(Lancamento.tipo == tipo)
        if categoria_id is not None:
            query = query.filter(Lancamento.categoria_id == categoria_id)
        if cliente_id is not None:
            query = query.filter(Lancamento.cliente_id == cliente_id)
        return query

    def buscar_por_filtros(self, **filtros) -> list[Lancamento]:
        query = self._filtrar(**filtros)
        return query.order_by(Lancamento.data_vencimento, Lancamento.lancamento_id).all()

    def buscar_paginado(self, page: int, page_size: int, **filtros) -> tuple[list[Lancamento], int]:
        query = self._filtrar(**filtros)
        total = query.count()
        itens = (
            query.order_by(Lancamento.data_vencimento, Lancamento.lancamento_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return itens, total

    def totais_por_status_e_tipo(
        self, **filtros
    ) -> list[Row[tuple[StatusLancamento, TipoLancamento, int, float]]]:
        query = self._filtrar(**filtros).with_entities(
            Lancamento.status, Lancamento.tipo, func.count(), func.sum(Lancamento.valor)
        )
        return query.group_by(Lancamento.status, Lancamento.tipo).all()

    def buscar_por_id(self, lancamento_id: int) -> Lancamento | None:
        return self.db.get(Lancamento, lancamento_id)

    def categoria_existe(self, categoria_id: int) -> bool:
        return self.db.get(CategoriaLancamento, categoria_id) is not None

    def cliente_existe(self, cliente_id: int) -> bool:
        return self.db.get(Cliente, cliente_id) is not None

    def criar(self, lancamento: Lancamento) -> Lancamento:
        self.db.add(lancamento)
        self.db.commit()
        self.db.refresh(lancamento)
        return lancamento

    def atualizar(self, lancamento: Lancamento) -> Lancamento:
        self.db.commit()
        self.db.refresh(lancamento)
        return lancamento

    def deletar(self, lancamento: Lancamento) -> None:
        self.db.delete(lancamento)
        self.db.commit()
