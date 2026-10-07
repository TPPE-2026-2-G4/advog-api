from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import exigir_permissao
from app.processo.schema import ProcessoCreate, ProcessoFilter, ProcessoResponse, ProcessoUpdate
from app.processo.service import ProcessoService

router = APIRouter(prefix="/processos", tags=["Processos"])


def get_processo_service(db: Session = Depends(get_db)) -> ProcessoService:
    return ProcessoService(db)


@router.post(
    "/",
    response_model=ProcessoResponse,
    status_code=201,
    dependencies=[Depends(exigir_permissao("criar_processos"))],
)
def criar_processo(
    processo: ProcessoCreate, service: ProcessoService = Depends(get_processo_service)
):
    try:
        return service.criar_processo(processo)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get(
    "/",
    response_model=list[ProcessoResponse],
    dependencies=[Depends(exigir_permissao("visualizar_processos"))],
)
def filtrar_processos(
    filtros: ProcessoFilter = Depends(), service: ProcessoService = Depends(get_processo_service)
):
    return service.buscar_processos(filtros)


@router.patch(
    "/{processo_id}",
    response_model=ProcessoResponse,
    dependencies=[Depends(exigir_permissao("editar_processos"))],
)
def atualizar_processo(
    processo_id: int,
    dados: ProcessoUpdate,
    service: ProcessoService = Depends(get_processo_service),
):
    try:
        return service.atualizar_processo(processo_id, dados)
    except ValueError as error:
        status_code = 409 if "CNJ já cadastrado" in str(error) else 404
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.delete(
    "/{processo_id}", status_code=204, dependencies=[Depends(exigir_permissao("excluir_processos"))]
)
def deletar_processo(processo_id: int, service: ProcessoService = Depends(get_processo_service)):
    try:
        service.deletar_processo(processo_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
