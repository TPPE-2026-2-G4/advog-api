from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import exigir_permissao
from app.processo.schema import (
    ProcessoCreate,
    ProcessoFilter,
    ProcessoPaginadoResponse,
    ProcessoResponse,
    ProcessoUpdate,
    SincronizacaoResponse,
)
from app.processo.service import ProcessoService

router = APIRouter(prefix="/processos", tags=["Processos"])


def get_processo_service(db: Session = Depends(get_db)) -> ProcessoService:
    return ProcessoService(db)


@router.post(
    "/sincronizar",
    response_model=SincronizacaoResponse,
    dependencies=[Depends(exigir_permissao("editar_processos"))],
)
async def sincronizar_processos():
    try:
        total = await ProcessoService.sincronizar_processos_com_api()
        return SincronizacaoResponse(
            atualizados=total,
            mensagem=f"{total} processos sincronizados com sucesso via Datajud.",
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao sincronizar processos com a API do Datajud: {error}",
        ) from error


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
    response_model=ProcessoPaginadoResponse,
    dependencies=[Depends(exigir_permissao("visualizar_processos"))],
)
def filtrar_processos(
    filtros: ProcessoFilter = Depends(), service: ProcessoService = Depends(get_processo_service)
):
    return service.buscar_processos(filtros)


@router.get(
    "/criticos/",
    response_model=list[ProcessoResponse],
    dependencies=[Depends(exigir_permissao("visualizar_processos"))],
)
def listar_processos_criticos(
    dias_sem_movimentacao: int = 30,
    funcionario_id: int | None = None,
    service: ProcessoService = Depends(get_processo_service),
):
    return service.buscar_processos_criticos(
        dias_sem_movimentacao=dias_sem_movimentacao,
        funcionario_id=funcionario_id,
    )


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
