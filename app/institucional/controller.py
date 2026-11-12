from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.atuacao.schema import AtuacaoResponse
from app.atuacao.service import AtuacaoService
from app.config.database import get_db
from app.core.dependencies import exigir_permissao, obter_funcionario_atual
from app.funcionario.model import Funcionario
from app.funcionario.schema import FuncionarioInstitucionalResponse
from app.funcionario.service import FuncionarioService
from app.institucional.repository import InstitucionalNaoEncontradoError
from app.institucional.schema import (
    AlertasConfigResponse,
    AlertasConfigUpdate,
    InstitucionalResponse,
    InstitucionalUpdate,
    InstitucionalUploadResponse,
)
from app.institucional.service import InstitucionalService, UploadInvalidoError

router = APIRouter(prefix="/institucional", tags=["Institucional"])


def obter_institucional_service(db: Session = Depends(get_db)) -> InstitucionalService:
    return InstitucionalService(db)


@router.get("", response_model=InstitucionalResponse)
def obter_configuracoes(
    service: InstitucionalService = Depends(obter_institucional_service),
):
    return service.obter_configuracoes()


@router.get("/equipe", response_model=list[FuncionarioInstitucionalResponse])
def obter_equipe_publica(db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    return service.buscar_visiveis_institucional()


@router.get("/atuacoes", response_model=list[AtuacaoResponse])
def obter_atuacoes_publicas(db: Session = Depends(get_db)):
    service = AtuacaoService(db)
    return service.buscar_visiveis_institucional()


@router.get("/alertas", response_model=AlertasConfigResponse)
def obter_configuracao_de_alertas(
    _: Funcionario = Depends(obter_funcionario_atual),
    service: InstitucionalService = Depends(obter_institucional_service),
):
    return service.obter_configuracao_de_alertas()


@router.patch(
    "/alertas",
    response_model=AlertasConfigResponse,
    summary="Definir antecedência dos prazos e dias para um processo ficar crítico",
    dependencies=[Depends(exigir_permissao("configuracoes_sistema"))],
)
def atualizar_configuracao_de_alertas(
    dados: AlertasConfigUpdate,
    service: InstitucionalService = Depends(obter_institucional_service),
):
    try:
        return service.atualizar_configuracao_de_alertas(dados.model_dump(exclude_none=True))
    except InstitucionalNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(erro)) from erro


@router.put(
    "",
    response_model=InstitucionalResponse,
    dependencies=[Depends(exigir_permissao("gerenciar_site"))],
)
def atualizar_configuracoes(
    dados: InstitucionalUpdate,
    service: InstitucionalService = Depends(obter_institucional_service),
):
    return service.atualizar_configuracoes(dados.model_dump(exclude_unset=True))


@router.post(
    "/upload/{tipo}",
    response_model=InstitucionalUploadResponse,
    dependencies=[Depends(exigir_permissao("gerenciar_site"))],
)
def upload_midia(
    tipo: str,
    file: UploadFile = File(...),
    service: InstitucionalService = Depends(obter_institucional_service),
):
    try:
        url_completa, warning = service.upload_midia(file, tipo)
        return {"url": url_completa, "warning": warning}
    except UploadInvalidoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
