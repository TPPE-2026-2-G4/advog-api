from sqlalchemy.orm import Session

from app.categoria_lancamento.model import CategoriaLancamento


class CategoriaLancamentoRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def buscar_todas(self) -> list[CategoriaLancamento]:
        return self.db.query(CategoriaLancamento).all()

    def buscar_por_id(self, categoria_id: int) -> CategoriaLancamento | None:
        return self.db.get(CategoriaLancamento, categoria_id)

    def buscar_por_nome(self, nome_categoria: str) -> CategoriaLancamento | None:
        return self.db.query(CategoriaLancamento).filter_by(nome_categoria=nome_categoria).first()

    def criar(self, categoria: CategoriaLancamento) -> CategoriaLancamento:
        self.db.add(categoria)
        self.db.commit()
        self.db.refresh(categoria)
        return categoria

    def atualizar(self, categoria: CategoriaLancamento) -> CategoriaLancamento:
        self.db.commit()
        self.db.refresh(categoria)
        return categoria

    def deletar(self, categoria: CategoriaLancamento) -> CategoriaLancamento:
        self.db.delete(categoria)
        self.db.commit()
        return categoria
