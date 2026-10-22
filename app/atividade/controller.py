from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.atividade.schema import KanbanResponse
from app.atividade.service import AtividadeService
from app.config.database import get_db
from app.core.dependencies import obter_funcionario_atual
from app.funcionario.model import Funcionario

router = APIRouter(prefix="/atividades", tags=["Atividades"])


def get_atividade_service(db: Session = Depends(get_db)) -> AtividadeService:
    return AtividadeService(db)


@router.get(
    "/kanban",
    response_model=KanbanResponse,
    summary="Visualizar o Kanban de atividades",
    responses={401: {"description": "Credenciais ausentes ou inválidas"}},
)
def visualizar_kanban(
    funcionario: Funcionario = Depends(obter_funcionario_atual),
    service: AtividadeService = Depends(get_atividade_service),
) -> KanbanResponse:
    return service.visualizar_kanban(funcionario)
