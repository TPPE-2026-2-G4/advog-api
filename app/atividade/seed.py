from sqlalchemy import select
from sqlalchemy.orm import Session

from app.atividade.model import EtapaKanban

ETAPAS_PADRAO = ("Backlog", "Em Execução", "Revisão", "Finalizado")


def inicializar_etapas_kanban(db: Session) -> None:
    """Inclui etapas ausentes; a transação é confirmada pelo chamador."""
    existentes = set(db.scalars(select(EtapaKanban.nome)))
    db.add_all(
        EtapaKanban(nome=nome, ordem=ordem)
        for ordem, nome in enumerate(ETAPAS_PADRAO, start=1)
        if nome not in existentes
    )
