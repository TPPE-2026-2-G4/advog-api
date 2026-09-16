from sqlalchemy.orm import Session

from app.models.processo import Processo, StatusProcesso


class ProcessoRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_todos(self) -> list[Processo]:
        return self.db.query(Processo).all()

    def buscar_por_id(self, processo_id: str) -> Processo | None:
        return self.db.query(Processo).filter(Processo.id == processo_id).first()

    def buscar_por_filtros(
        self,
        id: str | None = None,
        tribunal: str | None = None,
        titulo: str | None = None,
        cliente: str | None = None,
        area: str | None = None,
        responsavel: str | None = None,
        status: StatusProcesso | None = None,
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
        if status:
            query = query.filter(Processo.status == status)
        if prazo:
            query = query.filter(Processo.prazo.ilike(f"%{prazo}%"))

        return query.all()

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
