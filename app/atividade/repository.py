from datetime import date, datetime, time, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Query, Session

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

    def _montar_busca(
        self,
        atividade_id: int | None = None,
        titulo: str | None = None,
        descricao: str | None = None,
        etapa_id: int | None = None,
        processo_id: int | None = None,
        funcionario_id: int | None = None,
        prazo_inicio: date | None = None,
        prazo_fim: date | None = None,
        data_inicio_de: date | None = None,
        data_inicio_ate: date | None = None,
        realizada: bool | None = None,
        atrasada: bool | None = None,
        busca_textual: str | None = None,
    ) -> Query:
        query = self.db.query(Atividade)

        if atividade_id is not None:
            query = query.filter(Atividade.atividade_id == atividade_id)
        if titulo:
            query = query.filter(Atividade.titulo.ilike(f"%{titulo}%"))
        if descricao:
            query = query.filter(Atividade.descricao.ilike(f"%{descricao}%"))
        if etapa_id is not None:
            query = query.filter(Atividade.etapa_id == etapa_id)
        if processo_id is not None:
            query = query.filter(Atividade.processo_id == processo_id)
        if funcionario_id is not None:
            query = query.join(
                AtividadeFuncionario,
                AtividadeFuncionario.atividade_id == Atividade.atividade_id,
            ).filter(AtividadeFuncionario.funcionario_id == funcionario_id)
        if prazo_inicio is not None:
            query = query.filter(Atividade.data_prazo >= datetime.combine(prazo_inicio, time.min))
        if prazo_fim is not None:
            limite = datetime.combine(prazo_fim + timedelta(days=1), time.min)
            query = query.filter(Atividade.data_prazo < limite)
        if data_inicio_de is not None:
            query = query.filter(
                Atividade.data_inicio >= datetime.combine(data_inicio_de, time.min)
            )
        if data_inicio_ate is not None:
            limite = datetime.combine(data_inicio_ate + timedelta(days=1), time.min)
            query = query.filter(Atividade.data_inicio < limite)
        if realizada is True:
            query = query.filter(Atividade.data_realizado.isnot(None))
        elif realizada is False:
            query = query.filter(Atividade.data_realizado.is_(None))
        if atrasada is True:
            agora = datetime.now()
            query = query.filter(Atividade.data_realizado.is_(None), Atividade.data_prazo < agora)
        elif atrasada is False:
            agora = datetime.now()
            query = query.filter(
                or_(Atividade.data_realizado.isnot(None), Atividade.data_prazo >= agora)
            )
        if busca_textual:
            query = (
                query.outerjoin(Processo, Processo.processo_id == Atividade.processo_id)
                .outerjoin(
                    AtividadeFuncionario,
                    AtividadeFuncionario.atividade_id == Atividade.atividade_id,
                )
                .outerjoin(
                    Funcionario, Funcionario.funcionario_id == AtividadeFuncionario.funcionario_id
                )
                .filter(
                    or_(
                        Atividade.titulo.ilike(f"%{busca_textual}%"),
                        Atividade.descricao.ilike(f"%{busca_textual}%"),
                        Processo.titulo.ilike(f"%{busca_textual}%"),
                        Processo.cnj.ilike(f"%{busca_textual}%"),
                        Funcionario.nome.ilike(f"%{busca_textual}%"),
                    )
                )
                .distinct()
            )

        return query

    def buscar_por_filtros(
        self,
        atividade_id: int | None = None,
        titulo: str | None = None,
        descricao: str | None = None,
        etapa_id: int | None = None,
        processo_id: int | None = None,
        funcionario_id: int | None = None,
        prazo_inicio: date | None = None,
        prazo_fim: date | None = None,
        data_inicio_de: date | None = None,
        data_inicio_ate: date | None = None,
        realizada: bool | None = None,
        atrasada: bool | None = None,
        busca_textual: str | None = None,
    ) -> list[Atividade]:
        return (
            self._montar_busca(
                atividade_id=atividade_id,
                titulo=titulo,
                descricao=descricao,
                etapa_id=etapa_id,
                processo_id=processo_id,
                funcionario_id=funcionario_id,
                prazo_inicio=prazo_inicio,
                prazo_fim=prazo_fim,
                data_inicio_de=data_inicio_de,
                data_inicio_ate=data_inicio_ate,
                realizada=realizada,
                atrasada=atrasada,
                busca_textual=busca_textual,
            )
            .order_by(Atividade.atividade_id.desc())
            .all()
        )
