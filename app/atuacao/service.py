from sqlalchemy.orm import Session

from app.atuacao.model import Atuacao
from app.atuacao.repository import AtuacaoRepository
from app.atuacao.schema import AtuacaoCreate, AtuacaoUpdate


class AtuacaoService:
    def __init__(self, db_session: Session):
        self.repository = AtuacaoRepository(db_session)

    def buscar_todas(self) -> list[Atuacao]:
        return self.repository.buscar_todas()

    def buscar_visiveis_institucional(self) -> list[Atuacao]:
        return self.repository.buscar_visiveis_institucional()

    def buscar_por_id(self, atuacao_id: int) -> Atuacao:
        atuacao = self.repository.buscar_por_id(atuacao_id)
        if not atuacao:
            raise ValueError("Área de atuação não encontrada")
        return atuacao

    def criar_atuacao(self, dados: AtuacaoCreate) -> Atuacao:
        nome_limpo = dados.nome.strip()
        if self.repository.buscar_por_nome(nome_limpo):
            raise ValueError("Área de atuação já cadastrada")

        atuacao = Atuacao(
            nome=nome_limpo,
            descricao=dados.descricao.strip(),
            exibicao_institucional=dados.exibicao_institucional,
        )
        return self.repository.criar(atuacao)

    def atualizar_atuacao(self, atuacao_id: int, dados: AtuacaoUpdate) -> Atuacao:
        atuacao = self.buscar_por_id(atuacao_id)

        if dados.nome is not None:
            nome_limpo = dados.nome.strip()
            if nome_limpo != atuacao.nome and self.repository.buscar_por_nome(nome_limpo):
                raise ValueError("Área de atuação já cadastrada")
            atuacao.nome = nome_limpo

        if dados.descricao is not None:
            atuacao.descricao = dados.descricao.strip()

        if dados.exibicao_institucional is not None:
            atuacao.exibicao_institucional = dados.exibicao_institucional

        return self.repository.atualizar(atuacao)

    def mudar_exibicao_institucional(self, atuacao_id: int, exibicao: bool) -> Atuacao:
        atuacao = self.buscar_por_id(atuacao_id)
        atuacao.exibicao_institucional = exibicao
        return self.repository.atualizar(atuacao)

    def deletar_atuacao(self, atuacao_id: int) -> Atuacao:
        atuacao = self.buscar_por_id(atuacao_id)
        if self.repository.possui_funcionarios(atuacao_id):
            raise ValueError("Área de atuação está vinculada a funcionários")
        return self.repository.deletar(atuacao)
