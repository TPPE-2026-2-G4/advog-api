from sqlalchemy.orm import Session

from app.models.processo_model import Processo


class ProcessoRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, processo: Processo) -> Processo:
        self.db.add(processo)
        self.db.commit()
        self.db.refresh(processo)
        return processo

    def find_all_by_filters(
        self,
        id: str | None = None,
        tribunal: str | None = None,
        titulo: str | None = None,
        cliente: str | None = None,
        area: str | None = None,
        responsavel: str | None = None,
        status: str | None = None,
        prazo: str | None = None,
    ) -> list[Processo]:
        query = self.db.query(Processo)

        if id:
            query = query.filter(Processo.id.ilike(f"%{id}%"))
        if tribunal:
            query = query.filter(Processo.tribunal.ilike(f"%{tribunal}%"))
        if titulo:
            query = query.filter(Processo.titulo.ilike(f"%{titulo}%"))
        if cliente:
            query = query.filter(Processo.cliente.ilike(f"%{cliente}%"))
        if area:
            query = query.filter(Processo.area.ilike(f"%{area}%"))
        if responsavel:
            query = query.filter(Processo.responsavel.ilike(f"%{responsavel}%"))
        if status and status.lower() != "todos":
            query = query.filter(Processo.status.ilike(f"%{status}%"))
        if prazo:
            query = query.filter(Processo.prazo.ilike(f"%{prazo}%"))

        return query.all()
