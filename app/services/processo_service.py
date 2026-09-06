from sqlalchemy.orm import Session

from app.models.processo_model import Processo
from app.repositories.processo_repository import ProcessoRepository
from app.schemas.processo_filter import ProcessoFilter
from app.schemas.processo_schema import ProcessoCreate


class ProcessoService:
    def __init__(self, db_session: Session):
        self.repository = ProcessoRepository(db_session)

    def create_processo(self, processo_data: ProcessoCreate) -> Processo:
        processo_model = Processo(**processo_data.model_dump())
        return self.repository.save(processo_model)

    def search_processos(self, filters: ProcessoFilter) -> list[Processo]:
        return self.repository.find_all_by_filters(
            id=filters.id,
            tribunal=filters.tribunal,
            titulo=filters.titulo,
            cliente=filters.cliente,
            area=filters.area,
            responsavel=filters.responsavel,
            status=filters.status,
            prazo=filters.prazo,
        )
