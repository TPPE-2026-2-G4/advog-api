from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.atuacao.schema import (
    AtuacaoCreate,
    AtuacaoMudarExibicao,
    AtuacaoResponse,
    AtuacaoUpdate,
)
from app.atuacao.service import AtuacaoService
from app.config.database import get_db
from app.core.dependencies import exigir_permissao

router = APIRouter(prefix="/atuacoes", tags=["Áreas de Atuação"])


def _erro_http(e: ValueError) -> HTTPException:
    status_code = (
        status.HTTP_404_NOT_FOUND
        if str(e) == "Área de atuação não encontrada"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=status_code, detail=str(e))


@router.get("", response_model=list[AtuacaoResponse], status_code=status.HTTP_200_OK)
def buscar_todas_atuacoes(db: Session = Depends(get_db)):
    return AtuacaoService(db).buscar_todas()


@router.get("/{atuacao_id}", response_model=AtuacaoResponse, status_code=status.HTTP_200_OK)
def buscar_atuacao_por_id(atuacao_id: int, db: Session = Depends(get_db)):
    try:
        return AtuacaoService(db).buscar_por_id(atuacao_id)
    except ValueError as e:
        raise _erro_http(e) from e


@router.post(
    "",
    response_model=AtuacaoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_permissao("configuracoes_sistema"))],
)
def criar_atuacao(dados: AtuacaoCreate, db: Session = Depends(get_db)):
    try:
        return AtuacaoService(db).criar_atuacao(dados)
    except ValueError as e:
        raise _erro_http(e) from e


@router.put(
    "/{atuacao_id}",
    response_model=AtuacaoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(exigir_permissao("configuracoes_sistema"))],
)
def atualizar_atuacao(atuacao_id: int, dados: AtuacaoUpdate, db: Session = Depends(get_db)):
    try:
        return AtuacaoService(db).atualizar_atuacao(atuacao_id, dados)
    except ValueError as e:
        raise _erro_http(e) from e


@router.patch(
    "/{atuacao_id}/exibicao-institucional",
    response_model=AtuacaoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(exigir_permissao("configuracoes_sistema"))],
)
def mudar_exibicao_institucional(
    atuacao_id: int, dados: AtuacaoMudarExibicao, db: Session = Depends(get_db)
):
    try:
        return AtuacaoService(db).mudar_exibicao_institucional(
            atuacao_id, dados.exibicao_institucional
        )
    except ValueError as e:
        raise _erro_http(e) from e


@router.delete(
    "/{atuacao_id}",
    response_model=AtuacaoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(exigir_permissao("configuracoes_sistema"))],
)
def deletar_atuacao(atuacao_id: int, db: Session = Depends(get_db)):
    try:
        return AtuacaoService(db).deletar_atuacao(atuacao_id)
    except ValueError as e:
        raise _erro_http(e) from e
