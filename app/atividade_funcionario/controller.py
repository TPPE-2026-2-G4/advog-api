from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.atividade.schema import AtividadeResponse
from app.atividade.service import AtividadeNaoEncontradaError
from app.atividade_funcionario.schema import TrocarResponsavelRequest
from app.atividade_funcionario.service import (
    AtividadeFuncionarioService,
    ResponsavelJaAtribuidoError,
    ResponsavelNaoEncontradoError,
)
from app.config.database import get_db
from app.core.dependencies import exigir_permissao

router = APIRouter(prefix="/atividades", tags=["Atividades"])


def get_atividade_funcionario_service(
    db: Session = Depends(get_db),
) -> AtividadeFuncionarioService:
    return AtividadeFuncionarioService(db)


@router.patch(
    "/{atividade_id}/responsaveis/{funcionario_id}",
    response_model=AtividadeResponse,
    summary="Trocar um responsável da atividade por outro funcionário",
    dependencies=[Depends(exigir_permissao("editar_atividades"))],
    responses={
        401: {"description": "Credenciais ausentes ou inválidas"},
        403: {"description": "Sem permissão para editar atividades"},
        404: {"description": "Atividade ou responsável atual não encontrado"},
        409: {"description": "O novo funcionário já é responsável pela atividade"},
        422: {"description": "Novo funcionário inexistente"},
    },
)
def trocar_responsavel(
    atividade_id: int,
    funcionario_id: int,
    dados: TrocarResponsavelRequest,
    service: AtividadeFuncionarioService = Depends(get_atividade_funcionario_service),
):
    try:
        return service.trocar_responsavel(atividade_id, funcionario_id, dados.novo_funcionario_id)
    except (AtividadeNaoEncontradaError, ResponsavelNaoEncontradoError) as erro:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(erro)) from erro
    except ResponsavelJaAtribuidoError as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro
