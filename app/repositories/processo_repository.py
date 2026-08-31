from typing import List, Optional
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
        id: Optional[str] = None,
        tribunal: Optional[str] = None,
        titulo: Optional[str] = None,
        cliente: Optional[str] = None,
        area: Optional[str] = None,
        responsavel: Optional[str] = None,
        status: Optional[str] = None,
        prazo: Optional[str] = None
    ) -> List[Processo]:
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
