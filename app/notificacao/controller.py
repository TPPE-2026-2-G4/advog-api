import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import obter_funcionario_atual
from app.funcionario.model import Funcionario
from app.notificacao.model import TipoNotificacao
from app.notificacao.schema import (
    ContagemNaoLidasResponse,
    NotificacaoCreate,
    NotificacaoRead,
)
from app.notificacao.service import (
    NotificacaoAcessoNegadoError,
    NotificacaoNaoEncontradaError,
    NotificacaoService,
)

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


def get_notificacao_service(
    db: Session = Depends(get_db),
) -> NotificacaoService:
    return NotificacaoService(db)


RESPOSTAS_NOTIFICACAO: dict[int | str, dict[str, Any]] = {
    401: {"description": "Credenciais ausentes ou inválidas"},
    403: {"description": "Sem permissão para acessar o recurso"},
    404: {"description": "Notificação não encontrada"},
    422: {"description": "Dados de requisição inválidos"},
}


def _extrair_usuario_id(usuario: Funcionario) -> uuid.UUID:
    identificador = getattr(usuario, "id", None) or getattr(usuario, "funcionario_id", None)
    if isinstance(identificador, uuid.UUID):
        return identificador
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identificador de usuário inválido.",
    )


def _traduzir_erro(erro: ValueError) -> HTTPException:
    if isinstance(erro, NotificacaoNaoEncontradaError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(erro))
    if isinstance(erro, NotificacaoAcessoNegadoError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(erro))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro))


@router.get(
    "",
    response_model=list[NotificacaoRead],
    summary="Listar notificações do usuário autenticado",
    responses=RESPOSTAS_NOTIFICACAO,
)
def listar_notificacoes(
    apenas_nao_lidas: bool = Query(False, description="Filtrar apenas por notificações não lidas"),
    tipo: TipoNotificacao | None = Query(None, description="Filtrar por tipo de notificação"),
    limite: int = Query(50, ge=1, le=100, description="Quantidade máxima de itens"),
    offset: int = Query(0, ge=0, description="Quantidade de itens a ignorar"),
    usuario: Funcionario = Depends(obter_funcionario_atual),
    service: NotificacaoService = Depends(get_notificacao_service),
) -> list[NotificacaoRead]:
    usuario_id = _extrair_usuario_id(usuario)
    return service.listar_notificacoes(
        usuario_id=usuario_id,
        apenas_nao_lidas=apenas_nao_lidas,
        tipo=tipo,
        limite=limite,
        offset=offset,
    )


@router.get(
    "/nao-lidas/contagem",
    response_model=ContagemNaoLidasResponse,
    summary="Obter contagem de notificações não lidas",
    responses=RESPOSTAS_NOTIFICACAO,
)
def obter_contagem_nao_lidas(
    usuario: Funcionario = Depends(obter_funcionario_atual),
    service: NotificacaoService = Depends(get_notificacao_service),
) -> ContagemNaoLidasResponse:
    usuario_id = _extrair_usuario_id(usuario)
    return service.obter_contagem_nao_lidas(usuario_id)


@router.post(
    "",
    response_model=NotificacaoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar notificação",
    responses=RESPOSTAS_NOTIFICACAO,
)
def criar_notificacao(
    dados: NotificacaoCreate,
    _: Funcionario = Depends(obter_funcionario_atual),
    service: NotificacaoService = Depends(get_notificacao_service),
) -> NotificacaoRead:
    try:
        return service.criar_notificacao(dados)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro


@router.patch(
    "/marcar-todas-lidas",
    status_code=status.HTTP_200_OK,
    summary="Marcar todas as notificações do usuário como lidas",
    responses=RESPOSTAS_NOTIFICACAO,
)
def marcar_todas_como_lidas(
    usuario: Funcionario = Depends(obter_funcionario_atual),
    service: NotificacaoService = Depends(get_notificacao_service),
) -> dict[str, int]:
    usuario_id = _extrair_usuario_id(usuario)
    total_alterado = service.marcar_todas_como_lidas(usuario_id)
    return {"alteradas": total_alterado}


@router.patch(
    "/{notificacao_id}/lida",
    response_model=NotificacaoRead,
    summary="Marcar uma notificação específica como lida",
    responses=RESPOSTAS_NOTIFICACAO,
)
def marcar_como_lida(
    notificacao_id: uuid.UUID,
    usuario: Funcionario = Depends(obter_funcionario_atual),
    service: NotificacaoService = Depends(get_notificacao_service),
) -> NotificacaoRead:
    usuario_id = _extrair_usuario_id(usuario)
    try:
        return service.marcar_como_lida(notificacao_id, usuario_id)
    except ValueError as erro:
        raise _traduzir_erro(erro) from erro
