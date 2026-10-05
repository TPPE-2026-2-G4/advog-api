from math import ceil

from sqlalchemy.orm import Session

from app.processo.model import Processo
from app.processo.repository import ProcessoRepository
from app.processo.schema import (
    ProcessoCreate,
    ProcessoFilter,
    ProcessoPaginadoResponse,
    ProcessoResponse,
)


class ProcessoService:
    def __init__(self, db_session: Session):
        self.repository = ProcessoRepository(db_session)

    def create_processo(self, processo_data: ProcessoCreate) -> Processo:
        processo_model = Processo(**processo_data.model_dump())
        return self.repository.save(processo_model)

    def search_processos(self, filters: ProcessoFilter) -> ProcessoPaginadoResponse:
        itens, total = self.repository.find_paginated_by_filters(
            page=filters.page,
            page_size=filters.page_size,
            processo_id=filters.processo_id,
            cnj=filters.cnj,
            titulo_proc=filters.titulo_proc,
            descricao_proc=filters.descricao_proc,
            status=filters.status,
            tribunal=filters.tribunal,
            area=filters.area,
            cliente_id=filters.cliente_id,
            responsavel_id=filters.responsavel_id,
            busca=filters.busca,
            prazo_inicio=filters.prazo_inicio,
            prazo_fim=filters.prazo_fim,
        )
        return ProcessoPaginadoResponse(
            itens=[ProcessoResponse.model_validate(processo) for processo in itens],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=max(1, ceil(total / filters.page_size)),
        )
