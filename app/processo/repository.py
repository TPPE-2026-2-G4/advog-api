from datetime import date, datetime, time, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.cliente.model import Cliente
from app.processo.model import Processo


class ProcessoRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, processo: Processo) -> Processo:
        self.db.add(processo)
        self.db.commit()
        self.db.refresh(processo)
        return processo

    def find_paginated_by_filters(
        self,
        page: int,
        page_size: int,
        processo_id: int | None = None,
        cnj: str | None = None,
        titulo_proc: str | None = None,
        descricao_proc: str | None = None,
        status: str | None = None,
        tribunal: str | None = None,
        area: str | None = None,
        cliente_id: int | None = None,
        responsavel_id: int | None = None,
        busca: str | None = None,
        prazo_inicio: date | None = None,
        prazo_fim: date | None = None,
    ) -> tuple[list[Processo], int]:
        query = self.db.query(Processo)

        if processo_id is not None:
            query = query.filter(Processo.processo_id == processo_id)
        if cnj:
            query = query.filter(Processo.cnj.ilike(f"%{cnj}%"))
        if titulo_proc:
            query = query.filter(Processo.titulo_proc.ilike(f"%{titulo_proc}%"))
        if descricao_proc:
            query = query.filter(Processo.descricao_proc.ilike(f"%{descricao_proc}%"))
        if status and status.lower() != "todos":
            query = query.filter(Processo.status.ilike(f"%{status}%"))
        if tribunal:
            query = query.filter(Processo.tribunal.ilike(f"%{tribunal}%"))
        if area:
            query = query.filter(Processo.area.ilike(f"%{area}%"))
        if cliente_id is not None:
            query = query.filter(Processo.cliente_id == cliente_id)
        if responsavel_id is not None:
            query = query.filter(Processo.responsavel_id == responsavel_id)
        if busca:
            query = query.outerjoin(Cliente, Cliente.cliente_id == Processo.cliente_id).filter(
                or_(
                    Processo.cnj.ilike(f"%{busca}%"),
                    Processo.titulo_proc.ilike(f"%{busca}%"),
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
