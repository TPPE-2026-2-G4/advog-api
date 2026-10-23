from sqlalchemy.orm import Session

from app.atividade.model import Atividade
from app.atividade.repository import AtividadeRepository
from app.atividade.schema import (
    AtividadeCreate,
    AtividadeKanbanResponse,
    AtividadeResponse,
    AtividadeUpdate,
    EtapaKanbanResponse,
    KanbanResponse,
    ResponsavelKanbanResponse,
)
from app.funcionario.model import Funcionario


class AtividadeNaoEncontradaError(ValueError):
    pass


class DadosAtividadeInvalidosError(ValueError):
    pass


class AtividadeService:
    def __init__(self, db: Session):
        self.repository = AtividadeRepository(db)

    def buscar_atividade(self, atividade_id: int) -> AtividadeResponse:
        return AtividadeResponse.model_validate(self._obter(atividade_id))

    def criar_atividade(self, dados: AtividadeCreate) -> AtividadeResponse:
        campos = dados.model_dump(exclude={"responsaveis_ids"})
        self._validar_referencias(campos["etapa_id"], campos["processo_id"])
        atividade = Atividade(**campos)
        atividade.funcionarios = self._obter_responsaveis(dados.responsaveis_ids)
        return AtividadeResponse.model_validate(self.repository.criar(atividade))

    def atualizar_atividade(self, atividade_id: int, dados: AtividadeUpdate) -> AtividadeResponse:
        atividade = self._obter(atividade_id)
        alteracoes = dados.model_dump(exclude_unset=True, exclude={"responsaveis_ids"})

        inicio = alteracoes.get("data_inicio", atividade.data_inicio)
        prazo = alteracoes.get("data_prazo", atividade.data_prazo)
        realizado = alteracoes.get("data_realizado", atividade.data_realizado)
        if prazo < inicio or (realizado is not None and realizado < inicio):
            raise DadosAtividadeInvalidosError(
                "data_prazo e data_realizado não podem ser anteriores a data_inicio"
            )

        self._validar_referencias(alteracoes.get("etapa_id"), alteracoes.get("processo_id"))
        if dados.responsaveis_ids is not None:
            atividade.funcionarios = self._obter_responsaveis(dados.responsaveis_ids)

        for campo, valor in alteracoes.items():
            setattr(atividade, campo, valor)
        return AtividadeResponse.model_validate(self.repository.atualizar(atividade))

    def deletar_atividade(self, atividade_id: int) -> None:
        self.repository.deletar(self._obter(atividade_id))

    def _obter(self, atividade_id: int) -> Atividade:
        atividade = self.repository.buscar_por_id(atividade_id)
        if atividade is None:
            raise AtividadeNaoEncontradaError("Atividade não encontrada")
        return atividade

    def _validar_referencias(self, etapa_id: int | None, processo_id: int | None) -> None:
        if etapa_id is not None and not self.repository.existe_etapa(etapa_id):
            raise DadosAtividadeInvalidosError("Etapa do Kanban não encontrada")
        if processo_id is not None and not self.repository.existe_processo(processo_id):
            raise DadosAtividadeInvalidosError("Processo não encontrado")

    def _obter_responsaveis(self, funcionario_ids: list[int]) -> list[Funcionario]:
        if not funcionario_ids:
            return []
        funcionarios = self.repository.buscar_funcionarios(funcionario_ids)
        if len(funcionarios) != len(funcionario_ids):
            raise DadosAtividadeInvalidosError("Funcionário responsável não encontrado")
        return funcionarios

    def visualizar_kanban(self, funcionario: Funcionario) -> KanbanResponse:
        permissoes = funcionario.cargo.permissao or {}
        escopo_escritorio = permissoes.get("gerenciar_equipe", False)
        etapas = {
            etapa.etapa_id: EtapaKanbanResponse.model_validate(etapa)
            for etapa in self.repository.buscar_etapas()
        }
        atividades = self.repository.buscar_atividades(
            funcionario_id=None if escopo_escritorio else funcionario.funcionario_id
        )
        cartoes = {}
        for atividade in atividades:
            cartao = AtividadeKanbanResponse.model_validate(atividade)
            cartoes[atividade.atividade_id] = cartao
            etapas[atividade.etapa_id].atividades.append(cartao)

        for atividade_id, funcionario_id, nome in self.repository.buscar_responsaveis(
            list(cartoes)
        ):
            cartoes[atividade_id].responsaveis.append(
                ResponsavelKanbanResponse(funcionario_id=funcionario_id, nome=nome)
            )

        return KanbanResponse(
            escopo="escritorio" if escopo_escritorio else "usuario",
            etapas=list(etapas.values()),
        )
