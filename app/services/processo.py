from sqlalchemy.orm import Session

from app.models.processo import Processo
from app.repositories.processo import ProcessoRepository
from app.schemas.processo import ProcessoCreate, ProcessoUpdate
from app.schemas.processo_filter import ProcessoFilter


class ProcessoService:
    def __init__(self, db_session: Session):
        self.repository = ProcessoRepository(db_session)

    def buscar_todos(self) -> list[Processo]:
        return self.repository.buscar_todos()

    def buscar_por_filtros(self, filters: ProcessoFilter) -> list[Processo]:
        return self.repository.buscar_por_filtros(
            id=filters.id,
            tribunal=filters.tribunal,
            titulo=filters.titulo,
            cliente=filters.cliente,
            area=filters.area,
            responsavel=filters.responsavel,
            status=filters.status,
            prazo=filters.prazo,
        )

    def criar_processo(self, dados: ProcessoCreate) -> Processo:
        if self.repository.buscar_por_id(dados.id):
            raise ValueError("Processo já cadastrado")

        processo_model = Processo(**dados.model_dump())
        return self.repository.criar(processo_model)

    def atualizar_processo(self, processo_id: str, dados: ProcessoUpdate) -> Processo:
        processo = self.repository.buscar_por_id(processo_id)
        if processo is None:
            raise ValueError("Processo não encontrado")

        for key, value in dados.model_dump(exclude_unset=True).items():
            setattr(processo, key, value)

        return self.repository.atualizar(processo)

    def deletar_processo(self, processo_id: str) -> None:
        processo = self.repository.buscar_por_id(processo_id)
        if processo is None:
            raise ValueError("Processo não encontrado")

        self.repository.deletar(processo)
