import pytest

from app.atividade.model import Atividade, AtividadeFuncionario

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
        atividade = Atividade(titulo="Atividade de teste", etapa_id=etapas[nome_etapa].etapa_id)
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
    usuario.cargo.permissao = permissoes
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
    usuario.cargo.permissao = {"gerenciar_equipe": gerenciar_equipe}
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
