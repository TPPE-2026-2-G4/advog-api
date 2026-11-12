from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.atividade.schema import (
    AtividadeCreate,
    AtividadeFilter,
    AtividadeResponse,
    AtividadeUpdate,
    EtapaKanbanCreate,
    EtapaKanbanInfoResponse,
    EtapaKanbanReorder,
    EtapaKanbanUpdate,
    KanbanResponse,
    ProdutividadeResponse,
)
from app.atividade.service import (
    AtividadeNaoEncontradaError,
    AtividadeService,
    EtapaKanbanNaoEncontradaError,
)
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
    dependencies=[Depends(exigir_permissao("visualizar_atividades"))],
    responses={401: {"description": "Credenciais ausentes ou inválidas"}},
)
def visualizar_kanban(
    funcionario: Funcionario = Depends(obter_funcionario_atual),
    service: AtividadeService = Depends(get_atividade_service),
) -> KanbanResponse:
    return service.visualizar_kanban(funcionario)


RESPOSTAS_ESCRITA: dict[int | str, dict[str, Any]] = {
    401: {"description": "Credenciais ausentes ou inválidas"},
    403: {"description": "Sem permissão para executar a ação"},
    404: {"description": "Atividade não encontrada"},
    422: {"description": "Dados inválidos ou referência inexistente"},
}


def _traduzir_erro(erro: ValueError) -> HTTPException:
    if isinstance(erro, AtividadeNaoEncontradaError | EtapaKanbanNaoEncontradaError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(erro))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro))


@router.post(
    "",
    response_model=AtividadeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar atividade e delegar responsáveis",
    dependencies=[Depends(exigir_permissao("gerenciar_atividades"))],
    responses=RESPOSTAS_ESCRITA,
)
def criar_atividade(
    dados: AtividadeCreate,
    service: AtividadeService = Depends(get_atividade_service),
    usuario: Funcionario = Depends(obter_funcionario_atual),
):
    try:
        return service.criar_atividade(dados, ator_id=usuario.funcionario_id)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro


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
    dependencies=[Depends(exigir_permissao("visualizar_atividades"))],
    responses={401: {"description": "Credenciais ausentes ou inválidas"}},
)
def filtrar_atividades(
    filtros: Annotated[AtividadeFilter, Query()],
    usuario: Funcionario = Depends(obter_funcionario_atual),
    service: AtividadeService = Depends(get_atividade_service),
) -> list[AtividadeResponse]:
    return service.buscar_atividades(filtros, usuario)


@router.post(
    "/etapas",
    response_model=EtapaKanbanInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova etapa do Kanban",
    dependencies=[Depends(exigir_permissao("gerenciar_atividades"))],
    responses=RESPOSTAS_ESCRITA,
)
def criar_etapa(
    dados: EtapaKanbanCreate, service: AtividadeService = Depends(get_atividade_service)
) -> EtapaKanbanInfoResponse:
    try:
        return service.criar_etapa(dados)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro


@router.patch(
    "/etapas/reordenar",
    response_model=list[EtapaKanbanInfoResponse],
    summary="Reordenar etapas do Kanban",
    dependencies=[Depends(exigir_permissao("gerenciar_atividades"))],
    responses=RESPOSTAS_ESCRITA,
)
def reordenar_etapas(
    dados: EtapaKanbanReorder, service: AtividadeService = Depends(get_atividade_service)
) -> list[EtapaKanbanInfoResponse]:
    try:
        return service.reordenar_etapas(dados)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro


@router.patch(
    "/etapas/{etapa_id}",
    response_model=EtapaKanbanInfoResponse,
    summary="Renomear etapa do Kanban",
    dependencies=[Depends(exigir_permissao("gerenciar_atividades"))],
    responses=RESPOSTAS_ESCRITA,
)
def renomear_etapa(
    etapa_id: int,
    dados: EtapaKanbanUpdate,
    service: AtividadeService = Depends(get_atividade_service),
) -> EtapaKanbanInfoResponse:
    try:
        return service.renomear_etapa(etapa_id, dados)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro


@router.delete(
    "/etapas/{etapa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir etapa do Kanban",
    dependencies=[Depends(exigir_permissao("gerenciar_atividades"))],
    responses=RESPOSTAS_ESCRITA,
)
def deletar_etapa(
    etapa_id: int, service: AtividadeService = Depends(get_atividade_service)
) -> None:
    try:
        service.deletar_etapa(etapa_id)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro


@router.get(
    "/{atividade_id}",
    response_model=AtividadeResponse,
    summary="Detalhar atividade",
    dependencies=[Depends(exigir_permissao("visualizar_atividades"))],
    responses={401: RESPOSTAS_ESCRITA[401], 404: RESPOSTAS_ESCRITA[404]},
)
def buscar_atividade(
    atividade_id: int,
    usuario: Funcionario = Depends(obter_funcionario_atual),
    service: AtividadeService = Depends(get_atividade_service),
):
    try:
        return service.buscar_atividade(atividade_id, usuario=usuario)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro


@router.patch(
    "/{atividade_id}",
    response_model=AtividadeResponse,
    summary="Editar, mover de etapa ou redelegar atividade",
    dependencies=[Depends(exigir_permissao("gerenciar_atividades"))],
    responses=RESPOSTAS_ESCRITA,
)
def atualizar_atividade(
    atividade_id: int,
    dados: AtividadeUpdate,
    service: AtividadeService = Depends(get_atividade_service),
    usuario: Funcionario = Depends(obter_funcionario_atual),
):
    try:
        return service.atualizar_atividade(atividade_id, dados, ator_id=usuario.funcionario_id)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro


@router.delete(
    "/{atividade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir atividade",
    dependencies=[Depends(exigir_permissao("gerenciar_atividades"))],
    responses=RESPOSTAS_ESCRITA,
)
def deletar_atividade(
    atividade_id: int, service: AtividadeService = Depends(get_atividade_service)
):
    try:
        service.deletar_atividade(atividade_id)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro
