from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.atividade.model import Atividade, AtividadeFuncionario, EtapaKanban


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def resumir_atividades(
        self, inicio_do_dia: datetime, funcionario_id: int | None = None
    ) -> dict[str, int]:
        condicoes = {
            "pendentes": EtapaKanban.nome == "Backlog",
            "em_execucao": EtapaKanban.nome.not_in(("Backlog", "Finalizado")),
            "concluidas": EtapaKanban.nome == "Finalizado",
            "atrasadas": (EtapaKanban.nome != "Finalizado")
            & (Atividade.data_prazo < inicio_do_dia),
        }
        consulta = (
            select(
                *(
                    func.coalesce(func.sum(case((condicao, 1), else_=0)), 0).label(nome)
                    for nome, condicao in condicoes.items()
                )
            )
            .select_from(Atividade)
            .join(EtapaKanban, EtapaKanban.etapa_id == Atividade.etapa_id)
        )
        if funcionario_id is not None:
            vinculo = select(AtividadeFuncionario.atividade_id).where(
                AtividadeFuncionario.atividade_id == Atividade.atividade_id,
                AtividadeFuncionario.funcionario_id == funcionario_id,
            )
            consulta = consulta.where(vinculo.exists())

        return dict(self.db.execute(consulta).mappings().one())
