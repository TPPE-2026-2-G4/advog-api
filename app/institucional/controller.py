from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import exigir_permissao
from app.funcionario.service import FuncionarioService
from app.institucional.schema import (
    InstitucionalResponse,
    InstitucionalUpdate,
    InstitucionalUploadResponse,
    MembroEquipePublicaResponse,
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


@router.get("/equipe", response_model=list[MembroEquipePublicaResponse])
def obter_equipe_publica(db: Session = Depends(get_db)):
    service = FuncionarioService(db)
    return service.buscar_visiveis_institucional()


@router.put(
    "",
    response_model=InstitucionalResponse,
    dependencies=[Depends(exigir_permissao("configuracoes_sistema"))],
)
def atualizar_configuracoes(
    dados: InstitucionalUpdate,
    service: InstitucionalService = Depends(obter_institucional_service),
):
    return service.atualizar_configuracoes(dados.model_dump(exclude_unset=True))


@router.post(
    "/upload/{tipo}",
    response_model=InstitucionalUploadResponse,
    dependencies=[Depends(exigir_permissao("configuracoes_sistema"))],
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
