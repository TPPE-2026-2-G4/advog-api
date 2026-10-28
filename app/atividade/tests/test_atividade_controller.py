from datetime import datetime
from time import perf_counter

import pytest
from sqlalchemy import delete, insert

from app.atividade.model import Atividade
from app.atividade_funcionario.model import AtividadeFuncionario
from app.core.seguranca import criar_token_acesso
from app.etapa_kanban.model import EtapaKanban

ROTA = "/atividades/kanban"


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
def test_visualizar_kanban_respeita_acesso_e_contrato(
    client, db_session, funcionarios, atividades, token_acesso, permissoes, escopo, indice_usuario
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
            "busca": "nenhum resultado",
            "etapa_id": 99999,
        },
    )

    assert response.status_code == 200
    dados = response.json()
    assert set(dados) == {"escopo", "etapas"}
    assert dados["escopo"] == escopo
    assert [etapa["nome"] for etapa in dados["etapas"]] == [
        "Backlog",
        "Em Execução",
        "Aguardando cliente",
        "Revisão",
        "Finalizado",
    ]
    cartoes = [cartao for etapa in dados["etapas"] for cartao in etapa["atividades"]]
    if escopo == "escritorio":
        titulos = set(atividades)
    elif indice_usuario == 0:
        titulos = {"propria", "compartilhada", "finalizada"}
    else:
        titulos = {"terceiros", "compartilhada"}
    assert {cartao["titulo"] for cartao in cartoes} == titulos
    assert len(cartoes) == len(titulos)

    for etapa in dados["etapas"]:
        assert set(etapa) == {"etapa_id", "nome", "ordem", "atividades"}
        assert [cartao["atividade_id"] for cartao in etapa["atividades"]] == sorted(
            cartao["atividade_id"] for cartao in etapa["atividades"]
        )
        for cartao in etapa["atividades"]:
            atividade = atividades[cartao["titulo"]]
            assert atividade.etapa_id == etapa["etapa_id"]
            assert set(cartao) == {
                "atividade_id",
                "titulo",
                "data_prazo",
                "processo_id",
                "responsaveis",
            }
            assert cartao["data_prazo"] == "2026-10-30T15:30:00"
            assert cartao["processo_id"] == atividade.processo_id
            assert all(
                set(responsavel) == {"funcionario_id", "nome"}
                for responsavel in cartao["responsaveis"]
            )

    compartilhada = next(cartao for cartao in cartoes if cartao["titulo"] == "compartilhada")
    assert compartilhada["responsaveis"] == [
        {"funcionario_id": usuario.funcionario_id, "nome": usuario.nome} for usuario in funcionarios
    ]
    if escopo == "escritorio":
        sem_responsavel = next(
            cartao for cartao in cartoes if cartao["titulo"] == "sem_responsavel"
        )
        assert sem_responsavel["responsaveis"] == []
    assert dados["etapas"][2]["atividades"] == []


@pytest.mark.parametrize("gerenciar_equipe", [False, True])
@pytest.mark.parametrize("com_etapas", [False, True])
def test_kanban_vazio_nao_cria_etapas(
    client, db_session, funcionarios, token_acesso, request, gerenciar_equipe, com_etapas
):
    etapas = request.getfixturevalue("etapas") if com_etapas else {}
    if not com_etapas:
        db_session.execute(delete(EtapaKanban))
    usuario = funcionarios[0]
    usuario.cargo.permissao = {"gerenciar_equipe": gerenciar_equipe}
    db_session.commit()
    token = token_acesso(usuario.funcionario_id)

    response = client.get(ROTA, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    dados = response.json()
    assert dados["escopo"] == ("escritorio" if gerenciar_equipe else "usuario")
    assert len(dados["etapas"]) == len(etapas)
    assert all(etapa["atividades"] == [] for etapa in dados["etapas"])


@pytest.mark.parametrize("credencial", [None, "invalida", "expirada", "usuario_inexistente"])
def test_kanban_requer_autenticacao(client, token_acesso, credencial):
    headers = {}
    if credencial is not None:
        token = credencial
        if credencial == "expirada":
            token = criar_token_acesso({"sub": "1"}, tempo_expiracao_minutos=-1)
        elif credencial == "usuario_inexistente":
            token = token_acesso(99999)
        headers["Authorization"] = f"Bearer {token}"

    response = client.get(ROTA, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_openapi_documenta_somente_consulta_autenticada(client):
    schema = client.get("/openapi.json").json()

    operacoes = schema["paths"][ROTA]
    assert set(operacoes) == {"get"}
    consulta = operacoes["get"]
    assert consulta["security"] == [{"HTTPBearer": []}]
    assert "parameters" not in consulta
    assert consulta["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/KanbanResponse"
    }
    assert "401" in consulta["responses"]


@pytest.mark.parametrize("gerenciar_equipe", [False, True])
def test_kanban_com_dez_mil_atividades(
    client, db_session, etapas, funcionarios, token_acesso, record_property, gerenciar_equipe
):
    quantidade = 10_000
    usuario = funcionarios[0]
    usuario.cargo.permissao = {"gerenciar_equipe": gerenciar_equipe}
    funcionario_id = usuario.funcionario_id
    etapa_id = etapas["Backlog"].etapa_id
    db_session.execute(
        insert(Atividade),
        [
            {
                "atividade_id": indice,
                "titulo": f"Atividade {indice}",
                "descricao": "Descrição",
                "data_inicio": datetime(2026, 10, 1),
                "data_prazo": datetime(2026, 10, 30),
                "etapa_id": etapa_id,
            }
            for indice in range(1, quantidade + 1)
        ],
    )
    db_session.execute(
        insert(AtividadeFuncionario),
        [
            {"atividade_id": indice, "funcionario_id": funcionario_id}
            for indice in range(1, quantidade + 1)
        ],
    )
    db_session.commit()
    token = token_acesso(funcionario_id)

    inicio = perf_counter()
    response = client.get(ROTA, headers={"Authorization": f"Bearer {token}"})
    record_property("kanban_10000_segundos", perf_counter() - inicio)

    assert response.status_code == 200
    cartoes = response.json()["etapas"][0]["atividades"]
    assert len(cartoes) == quantidade
    assert [cartao["atividade_id"] for cartao in cartoes] == list(range(1, quantidade + 1))
    assert all(
        cartao["responsaveis"] == [{"funcionario_id": funcionario_id, "nome": "Funcionário 0"}]
        for cartao in cartoes
    )


def test_endpoint_produtividade(client, token_admin, funcionario_admin):
    resposta = client.get(
        "/atividades/produtividade",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resposta.status_code == 200
    assert resposta.json() == [
        {
            "funcionario_id": funcionario_admin.funcionario_id,
            "nome": funcionario_admin.nome,
            "finalizadas": 0,
            "a_fazer": 0,
            "em_andamento": 0,
            "atrasadas": 0,
            "progresso": 0,
        }
    ]


@pytest.mark.parametrize("autenticado, status", [(False, 401), (True, 403)])
def test_produtividade_requer_permissao(client, funcionarios, token_acesso, autenticado, status):
    headers = {}
    if autenticado:
        headers["Authorization"] = f"Bearer {token_acesso(funcionarios[0].funcionario_id)}"
    assert client.get("/atividades/produtividade", headers=headers).status_code == status


@pytest.mark.parametrize(
    ("autenticado", "params", "status_esperado", "titulos_esperados"),
    [
        (False, {}, 401, None),
        (
            True,
            {},
            200,
            {"propria", "terceiros", "compartilhada", "sem_responsavel", "finalizada"},
        ),
        (
            True,
            {"apenas_minhas": True},
            200,
            {"propria", "compartilhada", "finalizada"},
        ),
    ],
)
def test_filtrar_atividades(
    client,
    atividades,
    funcionarios,
    token_acesso,
    autenticado,
    params,
    status_esperado,
    titulos_esperados,
):
    headers = {}
    if autenticado:
        usuario = funcionarios[0]
        token = token_acesso(usuario.funcionario_id, usuario.email)
        headers["Authorization"] = f"Bearer {token}"

    response = client.get("/atividades/", headers=headers, params=params)

    assert response.status_code == status_esperado

    if status_esperado == 200:
        dados = response.json()
        assert isinstance(dados, list)
        titulos_obtidos = {item["titulo"] for item in dados}
        assert titulos_obtidos == titulos_esperados

        if dados:
            item = dados[0]
            assert set(item.keys()) == {
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
