from sqlalchemy.orm import Session

from app.categoria_lancamento.model import CategoriaLancamento
from app.categoria_lancamento.repository import CategoriaLancamentoRepository
from app.categoria_lancamento.schema import (
    CategoriaLancamentoCreate,
    CategoriaLancamentoUpdate,
)


class CategoriaLancamentoService:
    def __init__(self, db_session: Session):
        self.repository = CategoriaLancamentoRepository(db_session)

    def buscar_todas(self) -> list[CategoriaLancamento]:
        return self.repository.buscar_todas()

    def buscar_por_id(self, categoria_id: int) -> CategoriaLancamento:
        categoria = self.repository.buscar_por_id(categoria_id)
        if not categoria:
            raise ValueError("Categoria não encontrada")
        return categoria

    def criar_categoria(self, dados: CategoriaLancamentoCreate) -> CategoriaLancamento:
        if self.repository.buscar_por_nome(dados.nome_categoria):
            raise ValueError("Categoria já cadastrada")
        return self.repository.criar(CategoriaLancamento(**dados.model_dump()))

    def atualizar_categoria(
        self, categoria_id: int, dados: CategoriaLancamentoUpdate
    ) -> CategoriaLancamento:
        categoria = self.buscar_por_id(categoria_id)
        if dados.nome_categoria != categoria.nome_categoria:
            if self.repository.buscar_por_nome(dados.nome_categoria):
                raise ValueError("Categoria já cadastrada")
            categoria.nome_categoria = dados.nome_categoria
        return self.repository.atualizar(categoria)

    def deletar_categoria(self, categoria_id: int) -> CategoriaLancamento:
        categoria = self.buscar_por_id(categoria_id)
        if categoria.lancamentos:
            raise ValueError("Não é possível excluir uma categoria associada a lançamentos")
        return self.repository.deletar(categoria)
