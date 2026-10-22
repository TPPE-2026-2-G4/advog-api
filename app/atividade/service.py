from sqlalchemy.orm import Session

from app.atividade.repository import AtividadeRepository
from app.atividade.schema import (
    AtividadeKanbanResponse,
    EtapaKanbanResponse,
    KanbanResponse,
    ResponsavelKanbanResponse,
)
from app.funcionario.model import Funcionario


class AtividadeService:
    def __init__(self, db: Session):
        self.repository = AtividadeRepository(db)

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
