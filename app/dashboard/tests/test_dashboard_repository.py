from datetime import datetime

import pytest
from sqlalchemy import event

from app.atividade.model import Atividade
from app.dashboard.repository import DashboardRepository
from app.etapa_kanban.model import EtapaKanban

INICIO_DO_DIA = datetime(2026, 10, 15)


@pytest.mark.parametrize(
    ("nome_etapa", "contadores"),
    [
        ("Backlog", (1, 0, 0)),
        ("Em Execução", (0, 1, 0)),
        ("Revisão", (0, 1, 0)),
        ("Finalizado", (0, 0, 1)),
        ("Aguardando cliente", (0, 1, 0)),
    ],
)
@pytest.mark.parametrize(
    ("prazo", "vencida"),
    [
        (None, False),
        (datetime(2026, 10, 14, 23, 59, 59), True),
        (INICIO_DO_DIA, False),
        (datetime(2026, 10, 15, 1), False),
        (datetime(2026, 10, 15, 23, 59, 59), False),
        (datetime(2026, 10, 16), False),
    ],
)
def test_resumir_por_etapa_e_prazo(db_session, nome_etapa, contadores, prazo, vencida):
    etapa = EtapaKanban(nome=nome_etapa, ordem=99)
    db_session.add(etapa)
    db_session.flush()
    db_session.add(
        Atividade(
            titulo="Atividade de teste",
            etapa_id=etapa.etapa_id,
            data_prazo=prazo,
            data_inicio=datetime(2026, 10, 1),
            data_realizado=datetime(2026, 10, 14),
        )
    )
    db_session.commit()

    resultado = DashboardRepository(db_session).resumir_atividades(INICIO_DO_DIA)

    assert resultado == {
        "pendentes": contadores[0],
        "em_execucao": contadores[1],
        "concluidas": contadores[2],
        "atrasadas": int(vencida and nome_etapa != "Finalizado"),
    }


def test_resumo_executa_uma_consulta_sem_alterar_registros(db_session, etapas):
    atividade = Atividade(titulo="Sem prazo", etapa_id=etapas["Backlog"].etapa_id)
    db_session.add(atividade)
    db_session.commit()
    comandos = []

    def registrar_comando(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    conexao = db_session.connection()
    event.listen(conexao, "before_cursor_execute", registrar_comando)
    try:
        resultado = DashboardRepository(db_session).resumir_atividades(INICIO_DO_DIA)
    finally:
        event.remove(conexao, "before_cursor_execute", registrar_comando)

    assert resultado == {"pendentes": 1, "em_execucao": 0, "concluidas": 0, "atrasadas": 0}
    assert len(comandos) == 1
    assert comandos[0].lstrip().upper().startswith("SELECT")
