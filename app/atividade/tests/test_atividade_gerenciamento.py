import pytest
from sqlalchemy import select

from app.atividade.model import Atividade
from app.atividade_funcionario.model import AtividadeFuncionario

ROTA = "/atividades"


@pytest.fixture
def auth(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture
def payload(etapas, funcionarios):
    return {
        "titulo": "Protocolar petição",
        "descricao": "Protocolar a petição inicial",
        "data_inicio": "2026-10-01T09:00:00",
        "data_prazo": "2026-10-30T15:30:00",
        "etapa_id": etapas["Backlog"].etapa_id,
        "responsaveis_ids": [f.funcionario_id for f in funcionarios],
    }


def _ids_responsaveis(dados):
    return [r["funcionario_id"] for r in dados["responsaveis"]]


def test_criar_atividade_delega_responsaveis(client, auth, payload, funcionarios, processo):
    payload["processo_id"] = processo.processo_id

    response = client.post(ROTA, json=payload, headers=auth)

    assert response.status_code == 201
    dados = response.json()
    assert dados["titulo"] == payload["titulo"]
    assert dados["processo_id"] == processo.processo_id
    assert dados["data_realizado"] is None
    assert _ids_responsaveis(dados) == [f.funcionario_id for f in funcionarios]


def test_criar_atividade_sem_responsaveis_e_sem_processo(client, auth, payload):
    del payload["responsaveis_ids"]

    response = client.post(ROTA, json=payload, headers=auth)

    assert response.status_code == 201
    assert response.json()["responsaveis"] == []
    assert response.json()["processo_id"] is None


def test_criar_atividade_ignora_responsaveis_duplicados(client, auth, payload, funcionarios):
    unico = funcionarios[0].funcionario_id
    payload["responsaveis_ids"] = [unico, unico]

    response = client.post(ROTA, json=payload, headers=auth)

    assert response.status_code == 201
    assert _ids_responsaveis(response.json()) == [unico]


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("etapa_id", 99999),
        ("processo_id", 99999),
        ("responsaveis_ids", [99999]),
    ],
)
def test_criar_atividade_rejeita_referencia_inexistente(client, auth, payload, campo, valor):
    payload[campo] = valor

    response = client.post(ROTA, json=payload, headers=auth)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "alteracao",
    [
        {"data_prazo": "2026-09-30T00:00:00"},
        {"data_realizado": "2026-09-30T00:00:00"},
        {"titulo": ""},
        {"titulo": "x" * 101},
        {"descricao": "x" * 256},
    ],
)
def test_criar_atividade_valida_schema(client, auth, payload, alteracao):
    response = client.post(ROTA, json={**payload, **alteracao}, headers=auth)

    assert response.status_code == 422


def test_detalhar_atividade_para_qualquer_funcionario_autenticado(
    client, funcionarios, atividades, token_acesso
):
    usuario = funcionarios[0]
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get(
        f"{ROTA}/{atividades['compartilhada'].atividade_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    dados = response.json()
    assert set(dados) == {
        "atividade_id",
        "titulo",
        "descricao",
        "data_inicio",
        "data_prazo",
        "data_realizado",
        "etapa_id",
        "processo_id",
        "responsaveis",
    }
    assert _ids_responsaveis(dados) == sorted(f.funcionario_id for f in funcionarios)


def test_detalhar_atividade_inexistente(client, auth):
    assert client.get(f"{ROTA}/99999", headers=auth).status_code == 404


def test_atualizar_move_de_etapa_e_conclui(client, auth, atividades, etapas):
    atividade = atividades["propria"]

    response = client.patch(
        f"{ROTA}/{atividade.atividade_id}",
        json={
            "etapa_id": etapas["Finalizado"].etapa_id,
            "data_realizado": "2026-10-20T10:00:00",
        },
        headers=auth,
    )

    assert response.status_code == 200
    dados = response.json()
    assert dados["etapa_id"] == etapas["Finalizado"].etapa_id
    assert dados["data_realizado"] == "2026-10-20T10:00:00"
    assert dados["titulo"] == "propria"


def test_atualizar_redelega_substituindo_responsaveis(
    client, auth, db_session, atividades, funcionarios
):
    atividade = atividades["compartilhada"]

    response = client.patch(
        f"{ROTA}/{atividade.atividade_id}",
        json={"responsaveis_ids": [funcionarios[1].funcionario_id]},
        headers=auth,
    )

    assert response.status_code == 200
    assert _ids_responsaveis(response.json()) == [funcionarios[1].funcionario_id]
    vinculos = db_session.scalars(
        select(AtividadeFuncionario.funcionario_id).where(
            AtividadeFuncionario.atividade_id == atividade.atividade_id
        )
    ).all()
    assert vinculos == [funcionarios[1].funcionario_id]


def test_atualizar_sem_responsaveis_preserva_delegacao(client, auth, atividades, funcionarios):
    response = client.patch(
        f"{ROTA}/{atividades['compartilhada'].atividade_id}",
        json={"titulo": "Novo título"},
        headers=auth,
    )

    assert response.status_code == 200
    assert len(response.json()["responsaveis"]) == 2


def test_atualizar_lista_vazia_remove_responsaveis(client, auth, atividades):
    response = client.patch(
        f"{ROTA}/{atividades['compartilhada'].atividade_id}",
        json={"responsaveis_ids": []},
        headers=auth,
    )

    assert response.status_code == 200
    assert response.json()["responsaveis"] == []


def test_atualizar_processo_pode_ser_desvinculado(client, auth, atividades):
    response = client.patch(
        f"{ROTA}/{atividades['compartilhada'].atividade_id}",
        json={"processo_id": None},
        headers=auth,
    )

    assert response.status_code == 200
    assert response.json()["processo_id"] is None


@pytest.mark.parametrize(
    ("corpo", "status"),
    [
        ({"titulo": None}, 422),
        ({"etapa_id": None}, 422),
        ({"responsaveis_ids": None}, 422),
        ({"data_prazo": "2026-09-01T00:00:00"}, 422),
        ({"data_inicio": "2026-11-01T00:00:00"}, 422),
        ({"etapa_id": 99999}, 422),
        ({"processo_id": 99999}, 422),
        ({"responsaveis_ids": [99999]}, 422),
    ],
)
def test_atualizar_rejeita_dados_invalidos(client, auth, atividades, corpo, status):
    response = client.patch(
        f"{ROTA}/{atividades['propria'].atividade_id}", json=corpo, headers=auth
    )

    assert response.status_code == status


def test_atualizar_atividade_inexistente(client, auth):
    assert client.patch(f"{ROTA}/99999", json={"titulo": "x"}, headers=auth).status_code == 404


def test_excluir_remove_atividade_e_vinculos(client, auth, db_session, atividades):
    atividade_id = atividades["compartilhada"].atividade_id

    response = client.delete(f"{ROTA}/{atividade_id}", headers=auth)

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(Atividade, atividade_id) is None
    assert not db_session.scalars(
        select(AtividadeFuncionario).where(AtividadeFuncionario.atividade_id == atividade_id)
    ).all()
    assert client.get(f"{ROTA}/{atividade_id}", headers=auth).status_code == 404


def test_excluir_atividade_inexistente(client, auth):
    assert client.delete(f"{ROTA}/99999", headers=auth).status_code == 404


@pytest.mark.parametrize(
    ("metodo", "rota", "corpo"),
    [
        ("post", ROTA, "payload"),
        ("patch", f"{ROTA}/1", {"titulo": "x"}),
        ("delete", f"{ROTA}/1", None),
    ],
)
def test_escrita_exige_permissao_gerenciar_equipe(
    client, funcionarios, atividades, payload, token_acesso, metodo, rota, corpo
):
    usuario = funcionarios[0]
    token = token_acesso(usuario.funcionario_id, usuario.email)
    corpo = payload if corpo == "payload" else corpo

    response = client.request(
        metodo.upper(), rota, json=corpo, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("metodo", "rota"),
    [("post", ROTA), ("get", f"{ROTA}/1"), ("patch", f"{ROTA}/1"), ("delete", f"{ROTA}/1")],
)
def test_rotas_exigem_autenticacao(client, metodo, rota):
    assert getattr(client, metodo)(rota).status_code == 401


def test_relacionamentos_orm(db_session, atividades, etapas, funcionarios):
    compartilhada = atividades["compartilhada"]

    assert compartilhada.etapa is etapas["Revisão"]
    assert compartilhada in etapas["Revisão"].atividades_vinculadas
    assert [f.funcionario_id for f in compartilhada.funcionarios] == sorted(
        f.funcionario_id for f in funcionarios
    )


def test_excluir_atividade_via_orm_remove_vinculos(db_session, atividades):
    atividade = atividades["compartilhada"]
    atividade_id = atividade.atividade_id

    db_session.delete(atividade)
    db_session.commit()

    assert not db_session.scalars(
        select(AtividadeFuncionario).where(AtividadeFuncionario.atividade_id == atividade_id)
    ).all()


@pytest.mark.parametrize(
    ("permissao", "metodo", "rota", "corpo", "esperado"),
    [
        ("criar_atividades", "POST", ROTA, "payload", 201),
        ("editar_atividades", "PATCH", f"{ROTA}/ID", {"titulo": "x"}, 200),
        ("excluir_atividades", "DELETE", f"{ROTA}/ID", None, 204),
    ],
)
def test_cada_escrita_exige_somente_a_propria_permissao(
    client,
    db_session,
    funcionarios,
    atividades,
    payload,
    token_acesso,
    permissao,
    metodo,
    rota,
    corpo,
    esperado,
):
    usuario = funcionarios[0]
    todas = ("criar_atividades", "editar_atividades", "excluir_atividades")
    rota = rota.replace("ID", str(atividades["propria"].atividade_id))
    corpo = payload if corpo == "payload" else corpo
    headers = {"Authorization": f"Bearer {token_acesso(usuario.funcionario_id, usuario.email)}"}

    for liberada in (permissao, None):
        usuario.cargo.permissao = {p: p == liberada for p in todas} | {"gerenciar_equipe": True}
        db_session.commit()
        response = client.request(metodo, rota, json=corpo, headers=headers)
        assert response.status_code == (esperado if liberada else 403)


def test_criar_etapa_kanban(client, auth, etapas):
    response = client.post(f"{ROTA}/etapas", json={"nome": "  Validação Jurídica  "}, headers=auth)

    assert response.status_code == 201
    dados = response.json()
    assert dados["nome"] == "Validação Jurídica"
    assert dados["ordem"] == max(e.ordem for e in etapas.values()) + 1
    assert isinstance(dados["etapa_id"], int)


@pytest.mark.parametrize("nome", ["", "   ", "Backlog", "backlog", "Finalizado", "REVISÃO"])
def test_criar_etapa_rejeita_nome_vazio_ou_duplicado(client, auth, etapas, nome):
    response = client.post(f"{ROTA}/etapas", json={"nome": nome}, headers=auth)

    assert response.status_code == 422


def test_renomear_etapa_kanban(client, auth, etapas):
    etapa_id = etapas["Revisão"].etapa_id

    response = client.patch(
        f"{ROTA}/etapas/{etapa_id}", json={"nome": "Revisão Sênior"}, headers=auth
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Revisão Sênior"


@pytest.mark.parametrize("nome_protegido", ["Backlog", "Finalizado"])
def test_renomear_etapa_protegida_bloqueado(client, auth, etapas, nome_protegido):
    etapa_id = etapas[nome_protegido].etapa_id

    response = client.patch(f"{ROTA}/etapas/{etapa_id}", json={"nome": "Outro Nome"}, headers=auth)

    assert response.status_code == 422
    assert "Backlog e Finalizado" in response.json()["detail"]


@pytest.mark.parametrize("novo_nome", ["", "   ", "Backlog", "Finalizado", "Em Execução"])
def test_renomear_etapa_para_nome_invalido_ou_existente(client, auth, etapas, novo_nome):
    etapa_id = etapas["Revisão"].etapa_id

    response = client.patch(f"{ROTA}/etapas/{etapa_id}", json={"nome": novo_nome}, headers=auth)

    assert response.status_code == 422


def test_renomear_etapa_inexistente(client, auth):
    response = client.patch(f"{ROTA}/etapas/99999", json={"nome": "Nova"}, headers=auth)

    assert response.status_code == 404


def test_excluir_etapa_sem_atividades(client, auth, etapas):
    etapa_id = etapas["Aguardando cliente"].etapa_id

    response = client.delete(f"{ROTA}/etapas/{etapa_id}", headers=auth)

    assert response.status_code == 204
    kanban = client.get(f"{ROTA}/kanban", headers=auth).json()
    assert etapa_id not in [e["etapa_id"] for e in kanban["etapas"]]


@pytest.mark.parametrize("nome_protegido", ["Backlog", "Finalizado"])
def test_excluir_etapa_protegida_bloqueado(client, auth, etapas, nome_protegido):
    etapa_id = etapas[nome_protegido].etapa_id

    response = client.delete(f"{ROTA}/etapas/{etapa_id}", headers=auth)

    assert response.status_code == 422
    assert "Backlog e Finalizado" in response.json()["detail"]


def test_excluir_etapa_com_atividades_bloqueado(client, auth, atividades, etapas):
    etapa_id = etapas["Revisão"].etapa_id

    response = client.delete(f"{ROTA}/etapas/{etapa_id}", headers=auth)

    assert response.status_code == 422
    assert "possui atividades vinculadas" in response.json()["detail"]


def test_excluir_etapa_inexistente(client, auth):
    assert client.delete(f"{ROTA}/etapas/99999", headers=auth).status_code == 404


def test_reordenar_etapas_inclusive_backlog_e_finalizado(client, auth, etapas):
    ordem_invertida = [
        etapas["Finalizado"].etapa_id,
        etapas["Revisão"].etapa_id,
        etapas["Em Execução"].etapa_id,
        etapas["Aguardando cliente"].etapa_id,
        etapas["Backlog"].etapa_id,
    ]

    response = client.patch(
        f"{ROTA}/etapas/reordenar", json={"etapa_ids": ordem_invertida}, headers=auth
    )

    assert response.status_code == 200
    dados = response.json()
    assert [e["etapa_id"] for e in dados] == ordem_invertida
    assert [e["ordem"] for e in dados] == [1, 2, 3, 4, 5]

    kanban = client.get(f"{ROTA}/kanban", headers=auth).json()
    assert [e["etapa_id"] for e in kanban["etapas"]] == ordem_invertida


@pytest.mark.parametrize(
    "etapa_ids",
    [
        [],
        [1, 1],
        [1, 2],
        [1, 2, 3, 4, 99999],
    ],
)
def test_reordenar_etapas_rejeita_lista_invalida(client, auth, etapas, etapa_ids):
    response = client.patch(f"{ROTA}/etapas/reordenar", json={"etapa_ids": etapa_ids}, headers=auth)

    assert response.status_code == 422
