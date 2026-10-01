from sqlalchemy.orm import Session

from app.processo.model import Processo
from app.processo.repository import ProcessoRepository
from app.processo.schema import ProcessoCreate, ProcessoFilter, ProcessoUpdate


class ProcessoService:
    def __init__(self, db_session: Session):
        self.repository = ProcessoRepository(db_session)

    def buscar_todos(self) -> list[Processo]:
        return self.repository.buscar_todos()

    def buscar_processos(self, filters: ProcessoFilter) -> list[Processo]:
        return self.repository.buscar_por_filtros(
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

    def criar_processo(self, dados: ProcessoCreate) -> Processo:
        processo_existente = self.repository.buscar_por_cnj(dados.cnj)

        if processo_existente:
            raise ValueError("Processo já cadastrado")
        processo_model = Processo(**dados.model_dump())
        return self.repository.criar(processo_model)

    def atualizar_processo(self, processo_id: int, dados: ProcessoUpdate) -> Processo:
        processo = self.repository.buscar_por_id(processo_id)

        if processo is None:
            raise ValueError("Processo não encontrado")
        dados_atualizacao = dados.model_dump(exclude_unset=True)

        if "cnj" in dados_atualizacao:
            processo_existente = self.repository.buscar_por_cnj(dados_atualizacao["cnj"])

            if processo_existente is not None and processo_existente.processo_id != processo_id:
                raise ValueError("CNJ já cadastrado")

        for key, value in dados_atualizacao.items():
            setattr(processo, key, value)
        return self.repository.atualizar(processo)

    def deletar_processo(self, processo_id: int) -> None:
        processo = self.repository.buscar_por_id(processo_id)

        if processo is None:
            raise ValueError("Processo não encontrado")
        self.repository.deletar(processo)
