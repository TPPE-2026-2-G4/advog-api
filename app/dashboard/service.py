from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.dashboard.repository import DashboardRepository
from app.dashboard.schema import ResumoAtividadesResponse
from app.funcionario.model import Funcionario


class DashboardService:
    def __init__(self, db: Session):
        self.repository = DashboardRepository(db)

    def resumir_atividades(self, funcionario: Funcionario) -> ResumoAtividadesResponse:
        permissoes = funcionario.cargo.permissao or {}
        escopo_escritorio = permissoes.get("gerenciar_equipe", False)
        hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        inicio_do_dia = datetime.combine(hoje, time.min)
        totais = self.repository.resumir_atividades(
            inicio_do_dia,
            funcionario_id=None if escopo_escritorio else funcionario.funcionario_id,
        )
        return ResumoAtividadesResponse(
            escopo="escritorio" if escopo_escritorio else "usuario", **totais
        )
