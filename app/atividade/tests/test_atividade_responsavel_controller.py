import pytest
from sqlalchemy import select

from app.atividade_funcionario.model import AtividadeFuncionario


@pytest.fixture
def auth(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}


def rota(atividade_id, funcionario_id):
    return f"/atividades/{atividade_id}/responsaveis/{funcionario_id}"


def test_trocar_responsavel(client, auth, db_session, atividades, funcionarios, funcionario_admin):
    atividade = atividades["propria"]

    response = client.patch(
        rota(atividade.atividade_id, funcionarios[0].funcionario_id),
        json={"novo_funcionario_id": funcionario_admin.funcionario_id},
        headers=auth,
    )

    assert response.status_code == 200
    assert [r["funcionario_id"] for r in response.json()["responsaveis"]] == [
        funcionario_admin.funcionario_id
    ]
    db_session.expire_all()
    assert db_session.scalars(
        select(AtividadeFuncionario.funcionario_id).where(
            AtividadeFuncionario.atividade_id == atividade.atividade_id
        )
    ).all() == [funcionario_admin.funcionario_id]


def test_trocar_responsavel_preserva_os_demais(
    client, auth, atividades, funcionarios, funcionario_admin
):
    atividade = atividades["compartilhada"]

    response = client.patch(
        rota(atividade.atividade_id, funcionarios[0].funcionario_id),
        json={"novo_funcionario_id": funcionario_admin.funcionario_id},
        headers=auth,
    )

    assert response.status_code == 200
    assert {r["funcionario_id"] for r in response.json()["responsaveis"]} == {
        funcionarios[1].funcionario_id,
        funcionario_admin.funcionario_id,
    }


@pytest.mark.parametrize(
    ("atividade", "indice_atual", "novo", "status"),
    [
        ("inexistente", 0, "outro", 404),
        ("propria", 1, "outro", 404),
        ("compartilhada", 0, "colega", 409),
        ("propria", 0, "mesmo", 409),
        ("propria", 0, "inexistente", 422),
    ],
)
def test_trocar_responsavel_erros(
    client, auth, atividades, funcionarios, funcionario_admin, atividade, indice_atual, novo, status
):
    atividade_id = 99999 if atividade == "inexistente" else atividades[atividade].atividade_id
    novo_id = {
        "outro": funcionario_admin.funcionario_id,
        "colega": funcionarios[1].funcionario_id,
        "mesmo": funcionarios[0].funcionario_id,
        "inexistente": 99999,
    }[novo]

    response = client.patch(
        rota(atividade_id, funcionarios[indice_atual].funcionario_id),
        json={"novo_funcionario_id": novo_id},
        headers=auth,
    )

    assert response.status_code == status


def test_trocar_responsavel_exige_permissao(client, atividades, funcionarios, token_acesso):
    usuario = funcionarios[0]
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.patch(
        rota(atividades["propria"].atividade_id, usuario.funcionario_id),
        json={"novo_funcionario_id": funcionarios[1].funcionario_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_trocar_responsavel_exige_autenticacao(client):
    assert client.patch(rota(1, 1), json={"novo_funcionario_id": 2}).status_code == 401
