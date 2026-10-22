from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.dependencies import obter_funcionario_atual
from app.dashboard.schema import ResumoAtividadesResponse
from app.dashboard.service import DashboardService
from app.funcionario.model import Funcionario

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get(
    "/atividades/resumo",
    response_model=ResumoAtividadesResponse,
    summary="Resumir o estado das atividades",
    responses={401: {"description": "Credenciais ausentes ou inválidas"}},
)
def resumir_atividades(
    funcionario: Funcionario = Depends(obter_funcionario_atual),
    service: DashboardService = Depends(get_dashboard_service),
) -> ResumoAtividadesResponse:
    return service.resumir_atividades(funcionario)
