from sqlalchemy.orm import Session

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

    def buscar_por_filtros(
        self,
        processo_id: int | None = None,
        cnj: str | None = None,
        titulo: str | None = None,
        descricao: str | None = None,
        status: StatusProcesso | None = None,
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
        if responsavel_id is not None:
            query = query.filter(Processo.responsavel_id == responsavel_id)

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
