from datetime import date, datetime, time, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.cliente.model import Cliente
from app.processo.model import Processo, StatusProcesso


class ProcessoRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_todos(self) -> list[Processo]:
        return self.db.query(Processo).all()

    def buscar_por_id(self, processo_id: int) -> Processo | None:
        return self.db.query(Processo).filter(Processo.processo_id == processo_id).first()

    def buscar_por_cnj(self, cnj: str) -> Processo | None:
        return self.db.query(Processo).filter(Processo.cnj == cnj).first()

    def buscar_paginado_por_filtros(
        self,
        page: int,
        page_size: int,
        processo_id: int | None = None,
        cnj: str | None = None,
        titulo: str | None = None,
        descricao: str | None = None,
        status: StatusProcesso | None = None,
        tribunal: str | None = None,
        area: str | None = None,
        cliente_id: int | None = None,
        funcionario_id: int | None = None,
        busca: str | None = None,
        prazo_inicio: date | None = None,
        prazo_fim: date | None = None,
    ) -> tuple[list[Processo], int]:
        query = self.db.query(Processo)

        if processo_id is not None:
            query = query.filter(Processo.processo_id == processo_id)
        if cnj:
            query = query.filter(Processo.cnj.ilike(f"%{cnj}%"))
        if titulo:
            query = query.filter(Processo.titulo.ilike(f"%{titulo}%"))
        if descricao:
            query = query.filter(Processo.descricao.ilike(f"%{descricao}%"))
        if status is not None:
            query = query.filter(Processo.status == status)
        if tribunal:
            query = query.filter(Processo.tribunal.ilike(f"%{tribunal}%"))
        if area:
            query = query.filter(Processo.area.ilike(f"%{area}%"))
        if cliente_id is not None:
            query = query.filter(Processo.cliente_id == cliente_id)
        if funcionario_id is not None:
            query = query.filter(Processo.funcionario_id == funcionario_id)
        if busca:
            query = query.outerjoin(Cliente, Cliente.cliente_id == Processo.cliente_id).filter(
                or_(
                    Processo.cnj.ilike(f"%{busca}%"),
                    Processo.titulo.ilike(f"%{busca}%"),
                    Cliente.nome.ilike(f"%{busca}%"),
                )
            )
        if prazo_inicio is not None:
            query = query.filter(Processo.data_prazo >= datetime.combine(prazo_inicio, time.min))
        if prazo_fim is not None:
            limite = datetime.combine(prazo_fim + timedelta(days=1), time.min)
            query = query.filter(Processo.data_prazo < limite)

        total = query.count()
        itens = (
            query.order_by(Processo.processo_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return itens, total

    def criar(self, processo: Processo) -> Processo:
        self.db.add(processo)
        self.db.commit()
        self.db.refresh(processo)
        return processo

    def atualizar(self, processo: Processo) -> Processo:
        self.db.commit()
        self.db.refresh(processo)
        return processo

    def deletar(self, processo: Processo) -> None:
        self.db.delete(processo)
        self.db.commit()
