from sqlalchemy.orm import Session

from app.models.processo import Processo


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
        processo_id: int | None = None,
        cnj: str | None = None,
        titulo_proc: str | None = None,
        descricao_proc: str | None = None,
        status: str | None = None,
        tribunal: str | None = None,
        area: str | None = None,
        cliente_id: int | None = None,
        responsavel_id: int | None = None,
    ) -> list[Processo]:
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

        return query.all()
