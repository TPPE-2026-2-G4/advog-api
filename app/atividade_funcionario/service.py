from sqlalchemy.orm import Session

from app.atividade.schema import AtividadeResponse
from app.atividade.service import AtividadeNaoEncontradaError, DadosAtividadeInvalidosError
from app.atividade_funcionario.repository import AtividadeFuncionarioRepository


class ResponsavelNaoEncontradoError(ValueError):
    pass


class ResponsavelJaAtribuidoError(ValueError):
    pass


class AtividadeFuncionarioService:
    def __init__(self, db: Session):
        self.repository = AtividadeFuncionarioRepository(db)

    def trocar_responsavel(
        self, atividade_id: int, funcionario_id: int, novo_funcionario_id: int
    ) -> AtividadeResponse:
        atividade = self.repository.buscar_atividade(atividade_id)
        if atividade is None:
            raise AtividadeNaoEncontradaError("Atividade não encontrada")

        atual = next(
            (f for f in atividade.funcionarios if f.funcionario_id == funcionario_id), None
        )
        if atual is None:
            raise ResponsavelNaoEncontradoError("Funcionário não é responsável por esta atividade")

        if any(f.funcionario_id == novo_funcionario_id for f in atividade.funcionarios):
            raise ResponsavelJaAtribuidoError("Funcionário já é responsável por esta atividade")

        novo = self.repository.buscar_funcionario(novo_funcionario_id)
        if novo is None:
            raise DadosAtividadeInvalidosError("Novo funcionário responsável não encontrado")

        return AtividadeResponse.model_validate(
            self.repository.trocar_responsavel(atividade, atual, novo)
        )
