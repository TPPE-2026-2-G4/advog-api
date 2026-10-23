from sqlalchemy import select
from sqlalchemy.orm import Session

from app.atividade.model import Atividade
from app.atividade_funcionario.model import AtividadeFuncionario
from app.etapa_kanban.model import EtapaKanban
from app.funcionario.model import Funcionario
from app.processo.model import Processo


class AtividadeRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_etapas(self) -> list[EtapaKanban]:
        consulta = select(EtapaKanban).order_by(EtapaKanban.ordem, EtapaKanban.etapa_id)
        return list(self.db.scalars(consulta))

    def buscar_atividades(self, funcionario_id: int | None = None) -> list[Atividade]:
        consulta = select(Atividade).order_by(Atividade.atividade_id)
        if funcionario_id is not None:
            vinculo = select(AtividadeFuncionario.atividade_id).where(
                AtividadeFuncionario.atividade_id == Atividade.atividade_id,
                AtividadeFuncionario.funcionario_id == funcionario_id,
            )
            consulta = consulta.where(vinculo.exists())
        return list(self.db.scalars(consulta))

    def buscar_responsaveis(self, atividade_ids: list[int]) -> list[tuple[int, int, str]]:
        consulta = (
            select(
                AtividadeFuncionario.atividade_id,
                Funcionario.funcionario_id,
                Funcionario.nome,
            )
            .join(Funcionario, Funcionario.funcionario_id == AtividadeFuncionario.funcionario_id)
            .where(AtividadeFuncionario.atividade_id.in_(atividade_ids))
            .order_by(AtividadeFuncionario.atividade_id, Funcionario.funcionario_id)
        )
        return list(self.db.execute(consulta).tuples())

    def buscar_por_id(self, atividade_id: int) -> Atividade | None:
        return self.db.get(Atividade, atividade_id)

    def existe_etapa(self, etapa_id: int) -> bool:
        return self.db.get(EtapaKanban, etapa_id) is not None

    def existe_processo(self, processo_id: int) -> bool:
        return self.db.get(Processo, processo_id) is not None

    def buscar_funcionarios(self, funcionario_ids: list[int]) -> list[Funcionario]:
        consulta = (
            select(Funcionario)
            .where(Funcionario.funcionario_id.in_(funcionario_ids))
            .order_by(Funcionario.funcionario_id)
        )
        return list(self.db.scalars(consulta))

    def criar(self, atividade: Atividade) -> Atividade:
        self.db.add(atividade)
        self.db.commit()
        self.db.refresh(atividade)
        return atividade

    def atualizar(self, atividade: Atividade) -> Atividade:
        self.db.commit()
        self.db.refresh(atividade)
        return atividade

    def deletar(self, atividade: Atividade) -> None:
        self.db.delete(atividade)
        self.db.commit()
