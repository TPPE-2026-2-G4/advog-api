from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.atividade.model import Atividade
from app.atividade_funcionario.model import AtividadeFuncionario
from app.etapa_kanban.model import EtapaKanban
from app.funcionario.model import Funcionario


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

    def buscar_produtividade_equipe(self, inicio_do_dia: datetime) -> list[dict]:
        finalizada = EtapaKanban.nome == "Finalizado"
        no_prazo = Atividade.data_prazo >= inicio_do_dia
        condicoes = {
            "finalizadas": finalizada,
            "a_fazer": (EtapaKanban.nome == "Backlog") & no_prazo,
            "em_andamento": EtapaKanban.nome.not_in(("Backlog", "Finalizado")) & no_prazo,
            "atrasadas": (EtapaKanban.nome != "Finalizado")
            & (Atividade.data_prazo < inicio_do_dia),
        }
        consulta = (
            select(
                Funcionario.funcionario_id,
                Funcionario.nome,
                *(
                    func.coalesce(func.sum(case((condicao, 1), else_=0)), 0).label(nome)
                    for nome, condicao in condicoes.items()
                ),
            )
            .select_from(Funcionario)
            .outerjoin(
                AtividadeFuncionario,
                AtividadeFuncionario.funcionario_id == Funcionario.funcionario_id,
            )
            .outerjoin(Atividade, Atividade.atividade_id == AtividadeFuncionario.atividade_id)
            .outerjoin(EtapaKanban, EtapaKanban.etapa_id == Atividade.etapa_id)
            .group_by(Funcionario.funcionario_id, Funcionario.nome)
            .order_by(Funcionario.nome, Funcionario.funcionario_id)
        )
        return [dict(linha) for linha in self.db.execute(consulta).mappings()]
