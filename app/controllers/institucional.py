from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.dependencies.auth import exigir_permissao
from app.schemas.institucional import (
    InstitucionalResponse,
    InstitucionalUpdate,
    InstitucionalUploadResponse,
)
from app.services.institucional import InstitucionalService, UploadInvalidoError

router = APIRouter(prefix="/institucional", tags=["Institucional"])


def obter_institucional_service(db: Session = Depends(get_db)) -> InstitucionalService:
    return InstitucionalService(db)


@router.get("", response_model=InstitucionalResponse)
def obter_configuracoes(
    service: InstitucionalService = Depends(obter_institucional_service),
):
    return service.obter_configuracoes()


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
