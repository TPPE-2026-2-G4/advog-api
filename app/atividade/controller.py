from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.atividade.schema import (
    AtividadeFilter,
    AtividadeResponse,
    KanbanResponse,
    ProdutividadeResponse,
)
from app.atividade.service import AtividadeService
from app.config.database import get_db
from app.core.dependencies import exigir_permissao, obter_funcionario_atual
from app.funcionario.model import Funcionario

router = APIRouter(prefix="/atividades", tags=["Atividades"])


def get_atividade_service(db: Session = Depends(get_db)) -> AtividadeService:
    return AtividadeService(db)


@router.get(
    "/kanban",
    response_model=KanbanResponse,
    summary="Visualizar o Kanban de atividades",
    responses={401: {"description": "Credenciais ausentes ou inválidas"}},
)
def visualizar_kanban(
    funcionario: Funcionario = Depends(obter_funcionario_atual),
    service: AtividadeService = Depends(get_atividade_service),
) -> KanbanResponse:
    return service.visualizar_kanban(funcionario)


@router.get(
    "/produtividade",
    response_model=list[ProdutividadeResponse],
    summary="Visualizar a produtividade da equipe",
    dependencies=[Depends(exigir_permissao("gerenciar_equipe"))],
)
def visualizar_produtividade(
    service: AtividadeService = Depends(get_atividade_service),
) -> list[ProdutividadeResponse]:
    return service.visualizar_produtividade_equipe()


@router.get(
    "/",
    response_model=list[AtividadeResponse],
    summary="Filtrar e pesquisar atividades",
    responses={401: {"description": "Credenciais ausentes ou inválidas"}},
)
def filtrar_atividades(
    filtros: Annotated[AtividadeFilter, Query()],
    usuario: Funcionario = Depends(obter_funcionario_atual),
    service: AtividadeService = Depends(get_atividade_service),
) -> list[AtividadeResponse]:
    return service.buscar_atividades(filtros, usuario)
