from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import exigir_permissao, obter_funcionario_atual
from app.core.relatorio import FormatoRelatorio, resposta_arquivo
from app.funcionario.model import Funcionario
from app.processo.schema import (
    DocumentoProcessoResponse,
    DocumentoUrlResponse,
    ProcessoCreate,
    ProcessoFilter,
    ProcessoPaginadoResponse,
    ProcessoResponse,
    ProcessoResumoResponse,
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
    "/exportar",
    summary="Exportar processos em CSV, Excel ou PDF",
    description=(
        "Aceita os mesmos filtros de `GET /processos/` (a paginação é ignorada: "
        "todos os processos filtrados são exportados)."
    ),
    response_class=Response,
    responses={
        200: {"description": "Arquivo gerado", "content": {"application/octet-stream": {}}},
        422: {"description": "Parâmetros inválidos ou exportação acima do limite de linhas"},
    },
    dependencies=[Depends(exigir_permissao("visualizar_processos"))],
)
def exportar_processos(
    formato: FormatoRelatorio = Query(description="csv, xlsx ou pdf"),
    filtros: ProcessoFilter = Depends(),
    service: ProcessoService = Depends(get_processo_service),
):
    try:
        arquivo = service.exportar_processos(filtros, formato)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return resposta_arquivo(arquivo, "processos")


@router.get(
    "/resumo",
    response_model=ProcessoResumoResponse,
)
def obter_resumo_processos(
    dias_proximo_prazo: int = Query(
        7, ge=0, description="Quantidade de dias para considerar um processo próximo do prazo"
    ),
    funcionario_id: int | None = Query(
        None, description="Filtrar resumo por ID do funcionário (apenas administradores)"
    ),
    usuario_atual: Funcionario = Depends(exigir_permissao("visualizar_processos")),
    service: ProcessoService = Depends(get_processo_service),
):
    return service.obter_resumo_processos(
        usuario=usuario_atual,
        funcionario_id=funcionario_id,
        dias_proximo_prazo=dias_proximo_prazo,
    )


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


@router.post(
    "/{processo_id}/documentos",
    response_model=DocumentoProcessoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_permissao("editar_processos"))],
)
def upload_documento(
    processo_id: int,
    file: UploadFile = File(...),
    funcionario_atual: Funcionario = Depends(obter_funcionario_atual),
    service: ProcessoService = Depends(get_processo_service),
):
    try:
        return service.adicionar_documento(
            processo_id=processo_id,
            file=file,
            funcionario_id=funcionario_atual.funcionario_id,
            origem="manual",
        )
    except ValueError as error:
        status_code = 404 if "Processo não encontrado" in str(error) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.get(
    "/{processo_id}/documentos",
    response_model=list[DocumentoProcessoResponse],
    dependencies=[Depends(exigir_permissao("visualizar_processos"))],
)
def listar_documentos(
    processo_id: int,
    service: ProcessoService = Depends(get_processo_service),
):
    try:
        return service.listar_documentos(processo_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/{processo_id}/documentos/{documento_id}/url",
    response_model=DocumentoUrlResponse,
    dependencies=[Depends(exigir_permissao("visualizar_processos"))],
)
def obter_url_documento(
    processo_id: int,
    documento_id: int,
    expiracao_segundos: int = 1800,
    service: ProcessoService = Depends(get_processo_service),
):
    try:
        url = service.obter_url_documento(
            processo_id=processo_id,
            documento_id=documento_id,
            expiracao_segundos=expiracao_segundos,
        )
        return DocumentoUrlResponse(
            documento_id=documento_id,
            url=url,
            expira_em_segundos=expiracao_segundos,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete(
    "/{processo_id}/documentos/{documento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(exigir_permissao("editar_processos"))],
)
def deletar_documento(
    processo_id: int,
    documento_id: int,
    service: ProcessoService = Depends(get_processo_service),
):
    try:
        service.remover_documento(processo_id=processo_id, documento_id=documento_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
