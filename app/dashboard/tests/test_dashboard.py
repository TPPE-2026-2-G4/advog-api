from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event

from app.atividade.model import Atividade
from app.atividade_funcionario.model import AtividadeFuncionario
from app.cargo.model import Cargo
from app.dashboard.repository import DashboardRepository
from app.dashboard.service import DashboardService
from app.etapa_kanban.model import EtapaKanban
from app.funcionario.model import Funcionario

ROTA = "/dashboard/atividades/resumo"


@pytest.fixture
def atividades(db_session, etapas, funcionarios):
    distribuicao = [
        ("Backlog", [0]),
        ("Finalizado", [1]),
        ("Revisão", [0, 1]),
        ("Em Execução", [0, 1]),
        ("Backlog", []),
    ]
    for nome_etapa, indices in distribuicao:
        atividade = Atividade(
            titulo="Atividade de teste",
            descricao="Descrição de teste",
            data_inicio=datetime(2026, 10, 1),
            data_prazo=datetime(2099, 12, 31),
            etapa_id=etapas[nome_etapa].etapa_id,
        )
        db_session.add(atividade)
        db_session.flush()
        db_session.add_all(
            AtividadeFuncionario(
                atividade_id=atividade.atividade_id,
                funcionario_id=funcionarios[indice].funcionario_id,
            )
            for indice in indices
        )
    db_session.commit()


@pytest.mark.parametrize(
    ("permissoes", "escopo"),
    [
        ({}, "usuario"),
        ({"gerenciar_equipe": False}, "usuario"),
        ({"visualizar_equipe": True}, "usuario"),
        ({"gerenciar_equipe": True}, "escritorio"),
    ],
)
@pytest.mark.parametrize("indice_usuario", [0, 1])
def test_resumo_respeita_abrangencia_sem_duplicar_atividades(
    client,
    db_session,
    funcionarios,
    atividades,
    token_acesso,
    permissoes,
    escopo,
    indice_usuario,
):
    usuario = funcionarios[indice_usuario]
    usuario.cargo.permissao = {**permissoes, "visualizar_atividades": True}
    db_session.commit()
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get(
        ROTA,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "escopo": "escritorio",
            "funcionario_id": funcionarios[1 - indice_usuario].funcionario_id,
        },
    )

    assert response.status_code == 200
    if escopo == "escritorio":
        pendentes, concluidas = 2, 1
    else:
        pendentes, concluidas = 1 - indice_usuario, indice_usuario
    assert response.json() == {
        "escopo": escopo,
        "pendentes": pendentes,
        "em_execucao": 2,
        "concluidas": concluidas,
        "atrasadas": 0,
    }


@pytest.mark.parametrize("gerenciar_equipe", [False, True])
def test_resumo_sem_atividades_retorna_zeros(
    client, db_session, funcionarios, token_acesso, gerenciar_equipe
):
    usuario = funcionarios[0]
    usuario.cargo.permissao = {
        "gerenciar_equipe": gerenciar_equipe,
        "visualizar_atividades": True,
    }
    db_session.commit()
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get(ROTA, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "escopo": "escritorio" if gerenciar_equipe else "usuario",
        "pendentes": 0,
        "em_execucao": 0,
        "concluidas": 0,
        "atrasadas": 0,
    }


@pytest.mark.parametrize("credencial", [None, "invalida", "usuario_inexistente"])
def test_resumo_requer_autenticacao(client, token_acesso, credencial):
    headers = {}
    if credencial is not None:
        token = token_acesso(99999) if credencial == "usuario_inexistente" else credencial
        headers["Authorization"] = f"Bearer {token}"

    response = client.get(ROTA, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


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
            descricao="Descrição de teste",
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
    atividade = Atividade(
        titulo="Sem atraso",
        descricao="Descrição de teste",
        data_inicio=datetime(2026, 10, 1),
        data_prazo=INICIO_DO_DIA,
        etapa_id=etapas["Backlog"].etapa_id,
    )
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


@pytest.mark.parametrize(
    ("instante_utc", "inicio_esperado"),
    [
        (datetime(2026, 10, 15, 2, 59, 59, tzinfo=UTC), datetime(2026, 10, 14)),
        (datetime(2026, 10, 15, 3, tzinfo=UTC), datetime(2026, 10, 15)),
    ],
)
def test_resumo_usa_a_virada_do_dia_em_sao_paulo(instante_utc, inicio_esperado):
    service = DashboardService(MagicMock())
    service.repository = MagicMock()
    service.repository.resumir_atividades.return_value = {
        "pendentes": 0,
        "em_execucao": 0,
        "concluidas": 0,
        "atrasadas": 0,
    }
    funcionario = Funcionario(funcionario_id=1, cargo=Cargo(permissao={}))

    with patch("app.dashboard.service.datetime") as relogio:
        relogio.now.side_effect = instante_utc.astimezone
        relogio.combine.side_effect = datetime.combine
        resultado = service.resumir_atividades(funcionario)

    relogio.now.assert_called_once_with(ZoneInfo("America/Sao_Paulo"))
    service.repository.resumir_atividades.assert_called_once_with(inicio_esperado, funcionario_id=1)
    assert resultado.escopo == "usuario"
