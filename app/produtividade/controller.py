from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import exigir_permissao
from app.produtividade.schema import ProdutividadeResponse
from app.produtividade.service import ProdutividadeService

router = APIRouter(prefix="/produtividade", tags=["Produtividade"])


def get_produtividade_service(db: Session = Depends(get_db)) -> ProdutividadeService:
    return ProdutividadeService(db)


@router.get(
    "/",
    response_model=list[ProdutividadeResponse],
    dependencies=[Depends(exigir_permissao("gerenciar_equipe"))],
)
def visualizar_produtividade(
    service: ProdutividadeService = Depends(get_produtividade_service),
):
    return  # service.buscar_produtividade_equipe()
