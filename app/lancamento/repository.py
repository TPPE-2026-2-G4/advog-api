from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.categoria_lancamento.model import CategoriaLancamento
from app.cliente.model import Cliente
from app.lancamento.model import Lancamento, TipoLancamento


class LancamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_filtros(
        self,
        inicio: date | None = None,
        fim: date | None = None,
        tipo: TipoLancamento | None = None,
        categoria_id: int | None = None,
        cliente_id: int | None = None,
    ) -> list[Lancamento]:
        query = self.db.query(Lancamento)

        if inicio is not None:
            query = query.filter(Lancamento.data_vencimento >= datetime.combine(inicio, time.min))
        if fim is not None:
            limite = datetime.combine(fim + timedelta(days=1), time.min)
            query = query.filter(Lancamento.data_vencimento < limite)
        if tipo is not None:
            query = query.filter(Lancamento.tipo == tipo)
        if categoria_id is not None:
            query = query.filter(Lancamento.categoria_id == categoria_id)
        if cliente_id is not None:
            query = query.filter(Lancamento.cliente_id == cliente_id)

        return query.order_by(Lancamento.data_vencimento).all()

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
