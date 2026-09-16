from sqlalchemy.orm import Session

from app.models.processo import Processo
from app.repositories.processo import ProcessoRepository
from app.schemas.processo import ProcessoCreate, ProcessoFilter


class ProcessoService:
    def __init__(self, db_session: Session):
        self.repository = ProcessoRepository(db_session)

    def create_processo(self, processo_data: ProcessoCreate) -> Processo:
        processo_model = Processo(**processo_data.model_dump())
        return self.repository.save(processo_model)

    def search_processos(self, filters: ProcessoFilter) -> list[Processo]:
        return self.repository.find_all_by_filters(
            processo_id=filters.processo_id,
            cnj=filters.cnj,
            titulo=filters.titulo,
            descricao=filters.descricao,
            status=filters.status,
            tribunal=filters.tribunal,
            area=filters.area,
            cliente_id=filters.cliente_id,
            responsavel_id=filters.responsavel_id,
        )
