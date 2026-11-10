from datetime import date, datetime, time, timedelta
from time import perf_counter
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, event, insert, select

from app.atividade.model import Atividade
from app.atividade.repository import AtividadeRepository
from app.atividade.schema import (
    AtividadeFilter,
    AtividadeKanbanResponse,
    EtapaKanbanResponse,
    KanbanResponse,
    ProdutividadeResponse,
    ResponsavelKanbanResponse,
)
from app.atividade.service import AtividadeNaoEncontradaError, AtividadeService
from app.atividade_funcionario.model import AtividadeFuncionario
from app.cargo.model import Cargo
from app.core.seguranca import criar_token_acesso
from app.etapa_kanban.model import EtapaKanban
from app.funcionario.model import Funcionario

ROTA_KANBAN = "/atividades/kanban"


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
        ROTA_KANBAN,
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

    response = client.get(ROTA_KANBAN, headers={"Authorization": f"Bearer {token}"})

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

    response = client.get(ROTA_KANBAN, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_openapi_documenta_somente_consulta_autenticada(client):
    schema = client.get("/openapi.json").json()

    operacoes = schema["paths"][ROTA_KANBAN]
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
    response = client.get(ROTA_KANBAN, headers={"Authorization": f"Bearer {token}"})
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
            {"propria", "compartilhada", "finalizada"},
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


def _extrair_ids_responsaveis(dados):
    return [responsavel["funcionario_id"] for responsavel in dados["responsaveis"]]


def test_criar_atividade_delega_responsaveis(client, auth, payload, funcionarios, processo):
    payload["processo_id"] = processo.processo_id

    response = client.post(ROTA, json=payload, headers=auth)

    assert response.status_code == 201
    dados = response.json()
    assert dados["titulo"] == payload["titulo"]
    assert dados["processo_id"] == processo.processo_id
    assert dados["data_realizado"] is None
    assert _extrair_ids_responsaveis(dados) == [f.funcionario_id for f in funcionarios]


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
    assert _extrair_ids_responsaveis(response.json()) == [unico]


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


def test_detalhar_atividade_para_funcionario_responsavel(
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
    assert _extrair_ids_responsaveis(dados) == sorted(f.funcionario_id for f in funcionarios)


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
    assert _extrair_ids_responsaveis(response.json()) == [funcionarios[1].funcionario_id]
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


def test_buscar_etapas_preserva_vazias_e_desempata_por_id(db_session, etapas):
    resultado = AtividadeRepository(db_session).buscar_etapas()

    assert [etapa.nome for etapa in resultado] == [
        "Backlog",
        "Em Execução",
        "Aguardando cliente",
        "Revisão",
        "Finalizado",
    ]
    assert len(resultado) == len(etapas)


@pytest.mark.parametrize(
    ("indice_usuario", "titulos"),
    [
        (None, ["propria", "terceiros", "compartilhada", "sem_responsavel", "finalizada"]),
        (0, ["propria", "compartilhada", "finalizada"]),
        (1, ["terceiros", "compartilhada"]),
    ],
)
def test_buscar_atividades_respeita_vinculos_sem_duplicar(
    db_session, atividades, funcionarios, indice_usuario, titulos
):
    funcionario_id = None if indice_usuario is None else funcionarios[indice_usuario].funcionario_id

    resultado = AtividadeRepository(db_session).buscar_atividades(funcionario_id)

    assert [atividade.titulo for atividade in resultado] == titulos
    assert [atividade.atividade_id for atividade in resultado] == sorted(
        atividades[titulo].atividade_id for titulo in titulos
    )


@pytest.mark.parametrize("titulo", [None, "compartilhada", "sem_responsavel"])
def test_buscar_responsaveis_somente_dos_cartoes_solicitados(
    db_session, atividades, funcionarios, titulo
):
    ids = [] if titulo is None else [atividades[titulo].atividade_id]

    resultado = AtividadeRepository(db_session).buscar_responsaveis(ids)

    esperado = []
    if titulo == "compartilhada":
        esperado = [
            (atividades[titulo].atividade_id, usuario.funcionario_id, usuario.nome)
            for usuario in funcionarios
        ]
    assert resultado == esperado


@pytest.mark.parametrize(
    ("filtros_params", "titulos_esperados"),
    [
        ({}, ["Elaborar Petição Inicial", "Revisão de Contrato", "Audiência de Conciliação"]),
        ({"busca_textual": "Petição"}, ["Elaborar Petição Inicial"]),
        ({"busca_textual": "Análise"}, ["Revisão de Contrato"]),
        ({"busca_textual": "Termo Inexistente"}, []),
        ({"etapa_nome": "Backlog"}, ["Elaborar Petição Inicial"]),
        ({"indice_funcionario": 1}, ["Revisão de Contrato", "Audiência de Conciliação"]),
        ({"com_processo": True}, ["Elaborar Petição Inicial", "Audiência de Conciliação"]),
        (
            {"prazo_inicio": date(2026, 10, 1), "prazo_fim": date(2026, 10, 31)},
            ["Elaborar Petição Inicial", "Revisão de Contrato"],
        ),
        (
            {"data_inicio_de": date(2026, 9, 1), "data_inicio_ate": date(2026, 9, 30)},
            ["Audiência de Conciliação"],
        ),
        ({"filtrar_por_id_de": "Elaborar Petição Inicial"}, ["Elaborar Petição Inicial"]),
        ({"titulo": "Petição"}, ["Elaborar Petição Inicial"]),
        ({"descricao": "Análise"}, ["Revisão de Contrato"]),
        ({"realizada": True}, ["Audiência de Conciliação"]),
        ({"realizada": False}, ["Elaborar Petição Inicial", "Revisão de Contrato"]),
    ],
)
def test_buscar_por_filtros(
    db_session,
    atividades_para_filtro,
    etapas,
    funcionarios,
    processo,
    filtros_params,
    titulos_esperados,
):
    filtros_kwargs = {}

    if "filtrar_por_id_de" in filtros_params:
        atividade = (
            db_session.query(Atividade)
            .filter(Atividade.titulo == filtros_params["filtrar_por_id_de"])
            .first()
        )
        if atividade:
            filtros_kwargs["atividade_id"] = atividade.atividade_id
    if "titulo" in filtros_params:
        filtros_kwargs["titulo"] = filtros_params["titulo"]
    if "descricao" in filtros_params:
        filtros_kwargs["descricao"] = filtros_params["descricao"]
    if "busca_textual" in filtros_params:
        filtros_kwargs["busca_textual"] = filtros_params["busca_textual"]
    if "etapa_nome" in filtros_params:
        filtros_kwargs["etapa_id"] = etapas[filtros_params["etapa_nome"]].etapa_id
    if "indice_funcionario" in filtros_params:
        filtros_kwargs["funcionario_id"] = funcionarios[
            filtros_params["indice_funcionario"]
        ].funcionario_id
    if "com_processo" in filtros_params:
        filtros_kwargs["processo_id"] = (
            processo.processo_id if filtros_params["com_processo"] else None
        )
    if "prazo_inicio" in filtros_params:
        filtros_kwargs["prazo_inicio"] = filtros_params["prazo_inicio"]
    if "prazo_fim" in filtros_params:
        filtros_kwargs["prazo_fim"] = filtros_params["prazo_fim"]
    if "data_inicio_de" in filtros_params:
        filtros_kwargs["data_inicio_de"] = filtros_params["data_inicio_de"]
    if "data_inicio_ate" in filtros_params:
        filtros_kwargs["data_inicio_ate"] = filtros_params["data_inicio_ate"]
    if "realizada" in filtros_params:
        filtros_kwargs["realizada"] = filtros_params["realizada"]
    if "atrasada" in filtros_params:
        filtros_kwargs["atrasada"] = filtros_params["atrasada"]

    _ = AtividadeFilter.model_validate(filtros_kwargs)

    resultado = AtividadeRepository(db_session).buscar_por_filtros(**filtros_kwargs)

    titulos_obtidos = [atividade.titulo for atividade in resultado]
    if titulos_esperados is not None:
        assert sorted(titulos_obtidos) == sorted(titulos_esperados)
    else:
        assert isinstance(titulos_obtidos, list)


@pytest.mark.parametrize(
    ("nome_etapa", "prazo_offset_dias", "esperada_atrasada", "esperada_realizada"),
    [
        ("Backlog", -1, True, False),
        ("Em Execução", -1, True, False),
        ("Backlog", 0, False, False),
        ("Em Execução", 1, False, False),
        ("Finalizado", -1, False, True),
        ("Finalizado", 1, False, True),
    ],
)
def test_buscar_por_filtros_realizada_e_atrasada_usam_etapa_e_fuso_sp(
    db_session, etapas, nome_etapa, prazo_offset_dias, esperada_atrasada, esperada_realizada
):

    hoje_sp = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    inicio_do_dia = datetime.combine(hoje_sp, time.min)
    prazo = inicio_do_dia + timedelta(days=prazo_offset_dias)

    atividade = Atividade(
        titulo=f"Atividade Teste {nome_etapa} {prazo_offset_dias}",
        descricao="Desc",
        data_inicio=prazo - timedelta(days=5),
        data_prazo=prazo,
        data_realizado=None,
        etapa_id=etapas[nome_etapa].etapa_id,
    )
    db_session.add(atividade)
    db_session.commit()

    resultado_atrasada = AtividadeRepository(db_session).buscar_por_filtros(atrasada=True)
    resultado_nao_atrasada = AtividadeRepository(db_session).buscar_por_filtros(atrasada=False)
    resultado_realizada = AtividadeRepository(db_session).buscar_por_filtros(realizada=True)
    resultado_nao_realizada = AtividadeRepository(db_session).buscar_por_filtros(realizada=False)

    ids_atrasadas = [a.atividade_id for a in resultado_atrasada]
    ids_nao_atrasadas = [a.atividade_id for a in resultado_nao_atrasada]
    ids_realizadas = [a.atividade_id for a in resultado_realizada]
    ids_nao_realizadas = [a.atividade_id for a in resultado_nao_realizada]

    if esperada_atrasada:
        assert atividade.atividade_id in ids_atrasadas
        assert atividade.atividade_id not in ids_nao_atrasadas
    else:
        assert atividade.atividade_id not in ids_atrasadas
        assert atividade.atividade_id in ids_nao_atrasadas
    if esperada_realizada:
        assert atividade.atividade_id in ids_realizadas
        assert atividade.atividade_id not in ids_nao_realizadas
    else:
        assert atividade.atividade_id not in ids_realizadas
        assert atividade.atividade_id in ids_nao_realizadas


@pytest.mark.parametrize("quantidade", [0, 1, 5])
def test_kanban_executa_tres_consultas_sem_escrita(db_session, etapas, funcionarios, quantidade):
    etapa_id = etapas["Backlog"].etapa_id
    funcionario_id = funcionarios[0].funcionario_id
    if quantidade:
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
    usuario = Funcionario(
        atuacao_id=1, foto_perfil=1, funcionario_id=funcionario_id, cargo=Cargo(permissao={})
    )
    comandos = []

    def registrar_comando(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    conexao = db_session.connection()
    event.listen(conexao, "before_cursor_execute", registrar_comando)
    try:
        resultado = AtividadeService(db_session).visualizar_kanban(usuario)
    finally:
        event.remove(conexao, "before_cursor_execute", registrar_comando)

    assert len(comandos) == 3
    assert all(comando.lstrip().upper().startswith("SELECT") for comando in comandos)
    assert sum(len(etapa.atividades) for etapa in resultado.etapas) == quantidade
    assert db_session.query(Atividade).count() == quantidade
    assert db_session.query(AtividadeFuncionario).count() == quantidade


def test_produtividade_categorias_exclusivas_e_responsaveis(db_session, etapas, funcionarios):
    hoje = datetime(2026, 10, 22)
    casos = [
        ("Backlog", hoje),
        ("Em Execução", hoje),
        ("Revisão", hoje + timedelta(days=1)),
        ("Aguardando cliente", hoje),
        ("Backlog", hoje - timedelta(seconds=1)),
        ("Em Execução", hoje - timedelta(days=1)),
        ("Revisão", hoje - timedelta(days=1)),
        ("Finalizado", hoje - timedelta(days=1)),
    ]
    for indice, (etapa, prazo) in enumerate(casos):
        atividade = Atividade(
            titulo=f"Atividade {indice}",
            descricao="Teste",
            data_inicio=hoje - timedelta(days=2),
            data_prazo=prazo,
            etapa_id=etapas[etapa].etapa_id,
        )
        db_session.add(atividade)
        db_session.flush()
        db_session.add(
            AtividadeFuncionario(
                atividade_id=atividade.atividade_id,
                funcionario_id=funcionarios[0].funcionario_id,
            )
        )
        if etapa == "Finalizado":
            db_session.add(
                AtividadeFuncionario(
                    atividade_id=atividade.atividade_id,
                    funcionario_id=funcionarios[1].funcionario_id,
                )
            )
    db_session.flush()
    resultado = AtividadeRepository(db_session).buscar_produtividade_equipe(hoje)
    assert resultado == [
        {
            "funcionario_id": funcionarios[0].funcionario_id,
            "nome": funcionarios[0].nome,
            "finalizadas": 1,
            "a_fazer": 1,
            "em_andamento": 3,
            "atrasadas": 3,
        },
        {
            "funcionario_id": funcionarios[1].funcionario_id,
            "nome": funcionarios[1].nome,
            "finalizadas": 1,
            "a_fazer": 0,
            "em_andamento": 0,
            "atrasadas": 0,
        },
    ]


def test_produtividade_funcionarios_sem_atividades(db_session, funcionarios):
    resultado = AtividadeRepository(db_session).buscar_produtividade_equipe(datetime(2026, 10, 22))
    assert len(resultado) == 2
    for linha in resultado:
        assert all(
            linha[campo] == 0 for campo in ("finalizadas", "a_fazer", "em_andamento", "atrasadas")
        )


def test_produtividade_equipe_vazia(db_session):
    assert AtividadeRepository(db_session).buscar_produtividade_equipe(datetime(2026, 10, 22)) == []


@pytest.mark.parametrize(
    ("filtros", "titulos_esperados"),
    [
        (
            {"busca_textual": "Petição", "indice_funcionario": 0},
            ["Elaborar Petição Inicial"],
        ),
        (
            {"busca_textual": "Análise", "indice_funcionario": 1},
            ["Revisão de Contrato"],
        ),
        (
            {"busca_textual": "Audiência"},
            ["Audiência de Conciliação"],
        ),
    ],
)
def test_busca_textual_combinada_nao_causa_erro(
    db_session, atividades_para_filtro, funcionarios, filtros, titulos_esperados
):
    kwargs = {}
    if "busca_textual" in filtros:
        kwargs["busca_textual"] = filtros["busca_textual"]
    if "indice_funcionario" in filtros:
        kwargs["funcionario_id"] = funcionarios[filtros["indice_funcionario"]].funcionario_id

    resultado = AtividadeRepository(db_session).buscar_por_filtros(**kwargs)
    assert [a.titulo for a in resultado] == titulos_esperados


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


@pytest.mark.parametrize("processo_id", [None, 12])
def test_cartao_serializa_somente_campos_de_visualizacao(processo_id):
    atividade = Atividade(
        atividade_id=1,
        titulo="Preparar defesa",
        descricao="Descrição detalhada",
        data_inicio=datetime(2026, 10, 1),
        data_prazo=datetime(2026, 10, 30, 15, 30),
        etapa_id=1,
        processo_id=processo_id,
    )

    cartao = AtividadeKanbanResponse.model_validate(atividade)

    assert cartao.model_dump(mode="json") == {
        "atividade_id": 1,
        "titulo": "Preparar defesa",
        "data_prazo": "2026-10-30T15:30:00",
        "processo_id": processo_id,
        "responsaveis": [],
    }


def test_etapas_vazias_possuem_listas_independentes():
    etapa = EtapaKanban(etapa_id=1, nome="Backlog", ordem=1)

    primeira = EtapaKanbanResponse.model_validate(etapa)
    segunda = EtapaKanbanResponse.model_validate(etapa)

    assert primeira.atividades == []
    assert primeira.atividades is not segunda.atividades


def test_kanban_rejeita_escopo_desconhecido():
    with pytest.raises(ValidationError):
        KanbanResponse.model_validate({"escopo": "todos", "etapas": []})


def test_produtividade_serializa_contrato():
    dados = {
        "funcionario_id": 7,
        "nome": "Responsável",
        "finalizadas": 1,
        "a_fazer": 1,
        "em_andamento": 3,
        "atrasadas": 3,
        "progresso": 12.5,
    }
    assert ProdutividadeResponse.model_validate(dados).model_dump(mode="json") == dados


@pytest.mark.parametrize(
    "campo",
    ["funcionario_id", "nome", "finalizadas", "a_fazer", "em_andamento", "atrasadas", "progresso"],
)
def test_produtividade_exige_campos_do_contrato(campo):
    dados = {
        "funcionario_id": 7,
        "nome": "Responsável",
        "finalizadas": 0,
        "a_fazer": 0,
        "em_andamento": 0,
        "atrasadas": 0,
        "progresso": 0.0,
    }
    del dados[campo]
    with pytest.raises(ValidationError):
        ProdutividadeResponse.model_validate(dados)


@pytest.mark.parametrize(
    ("inputs", "esperados"),
    [
        (
            {},
            {
                "apenas_minhas": False,
                "atividade_id": None,
                "titulo": None,
                "descricao": None,
                "etapa_id": None,
                "processo_id": None,
                "funcionario_id": None,
                "prazo_inicio": None,
                "prazo_fim": None,
                "data_inicio_de": None,
                "data_inicio_ate": None,
                "realizada": None,
                "atrasada": None,
                "busca_textual": None,
            },
        ),
        (
            {
                "atividade_id": 10,
                "titulo": "Elaborar recurso",
                "descricao": "Recurso de apelação",
                "etapa_id": 2,
                "processo_id": 5,
                "funcionario_id": 7,
                "prazo_inicio": date(2026, 10, 1),
                "prazo_fim": date(2026, 10, 31),
                "data_inicio_de": date(2026, 10, 1),
                "data_inicio_ate": date(2026, 10, 15),
                "realizada": False,
                "atrasada": True,
                "apenas_minhas": False,
                "busca_textual": "recurso apelação",
            },
            {
                "atividade_id": 10,
                "titulo": "Elaborar recurso",
                "descricao": "Recurso de apelação",
                "etapa_id": 2,
                "processo_id": 5,
                "funcionario_id": 7,
                "prazo_inicio": date(2026, 10, 1),
                "prazo_fim": date(2026, 10, 31),
                "data_inicio_de": date(2026, 10, 1),
                "data_inicio_ate": date(2026, 10, 15),
                "realizada": False,
                "atrasada": True,
                "apenas_minhas": False,
                "busca_textual": "recurso apelação",
            },
        ),
    ],
)
def test_atividade_filter_instanciacao_e_valores(inputs, esperados):
    filtro = AtividadeFilter(**inputs)
    for campo, valor_esperado in esperados.items():
        assert getattr(filtro, campo) == valor_esperado


@pytest.mark.parametrize(
    ("dados_datas", "mensagem_erro"),
    [
        (
            {"prazo_inicio": date(2026, 10, 31), "prazo_fim": date(2026, 10, 1)},
            "prazo_inicio não pode ser posterior a prazo_fim",
        ),
        (
            {"data_inicio_de": date(2026, 10, 20), "data_inicio_ate": date(2026, 10, 10)},
            "data_inicio_de não pode ser posterior a data_inicio_ate",
        ),
    ],
)
def test_atividade_filter_valida_intervalos_de_datas_invalidos(dados_datas, mensagem_erro):
    with pytest.raises(ValidationError) as exc_info:
        AtividadeFilter(**dados_datas)

    assert mensagem_erro in str(exc_info.value)


@pytest.mark.parametrize(
    "dados_datas",
    [
        {"prazo_inicio": date(2026, 10, 1), "prazo_fim": date(2026, 10, 31)},
        {"prazo_inicio": date(2026, 10, 1), "prazo_fim": date(2026, 10, 1)},
        {"data_inicio_de": date(2026, 10, 10), "data_inicio_ate": date(2026, 10, 20)},
        {"data_inicio_de": date(2026, 10, 10), "data_inicio_ate": date(2026, 10, 10)},
    ],
)
def test_atividade_filter_valida_intervalos_de_datas_validos(dados_datas):
    filtro = AtividadeFilter(**dados_datas)
    for campo, valor in dados_datas.items():
        assert getattr(filtro, campo) == valor


@pytest.mark.parametrize(
    ("campo", "tamanho"),
    [
        ("titulo", 101),
        ("descricao", 256),
    ],
)
def test_atividade_filter_limite_maximo_dos_campos(campo, tamanho):
    dados = {campo: "a" * tamanho}
    with pytest.raises(ValidationError):
        AtividadeFilter(**dados)


@pytest.mark.parametrize("campo", ["prazo_fim", "data_inicio_ate"])
def test_atividade_filter_rejeita_date_max_que_causaria_overflow(campo: str):
    with pytest.raises(ValidationError):
        AtividadeFilter.model_validate({campo: date.max})


@pytest.mark.parametrize("campo", ["prazo_fim", "data_inicio_ate"])
def test_atividade_filter_aceita_um_dia_antes_de_date_max(campo: str):
    data_segura = date.max - timedelta(days=1)
    filtro = AtividadeFilter.model_validate({campo: data_segura})
    assert getattr(filtro, campo) == data_segura


@pytest.mark.parametrize(
    ("campo", "data"),
    [
        ("prazo_fim", date(9999, 1, 31)),
        ("prazo_fim", date(9999, 11, 30)),
        ("data_inicio_ate", date(9999, 2, 28)),
    ],
)
def test_atividade_filter_aceita_fins_de_mes_em_9999(campo: str, data: date):
    filtro = AtividadeFilter.model_validate({campo: data})
    assert getattr(filtro, campo) == data


def test_atividade_filter_rejeita_apenas_minhas_com_funcionario_id():
    with pytest.raises(ValidationError) as exc_info:
        AtividadeFilter.model_validate({"apenas_minhas": True, "funcionario_id": 99})
    assert "apenas_minhas e funcionario_id não podem ser usados simultaneamente" in str(
        exc_info.value
    )


@pytest.mark.parametrize(
    "dados",
    [
        {"apenas_minhas": True},
        {"funcionario_id": 99},
        {"apenas_minhas": False, "funcionario_id": 99},
    ],
)
def test_atividade_filter_aceita_combinacoes_validas_de_escopo(dados):
    filtro = AtividadeFilter(**dados)
    for campo, valor in dados.items():
        assert getattr(filtro, campo) == valor


@pytest.mark.parametrize(
    ("usuario_id", "responsaveis_ids", "espera_erro"),
    [
        (7, [7], False),
        (7, [8], True),
    ],
)
def test_buscar_atividade_valida_acesso_do_responsavel(usuario_id, responsaveis_ids, espera_erro):
    service = AtividadeService(MagicMock())
    service.repository = MagicMock()
    service.repository.buscar_por_id.return_value = Atividade(
        atividade_id=10,
        titulo="Atividade",
        descricao="Descrição",
        data_inicio=datetime(2026, 10, 1),
        data_prazo=datetime(2026, 10, 30),
        etapa_id=1,
        funcionarios=[
            Funcionario(
                atuacao_id=1,
                foto_perfil=1,
                funcionario_id=responsavel_id,
                nome=f"Responsável {responsavel_id}",
            )
            for responsavel_id in responsaveis_ids
        ],
    )
    usuario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        funcionario_id=usuario_id,
        cargo=Cargo(permissao={}),
    )

    if espera_erro:
        with pytest.raises(AtividadeNaoEncontradaError, match="Atividade não encontrada"):
            service.buscar_atividade(10, usuario=usuario)
    else:
        resultado = service.buscar_atividade(10, usuario=usuario)
        assert resultado.atividade_id == 10


@pytest.mark.parametrize(
    ("permissoes", "escopo", "funcionario_id"),
    [
        (None, "usuario", 7),
        ({}, "usuario", 7),
        ({"gerenciar_equipe": False}, "usuario", 7),
        ({"visualizar_equipe": True}, "usuario", 7),
        ({"gerenciar_equipe": True}, "escritorio", None),
    ],
)
def test_kanban_determina_escopo_e_agrupa_cartoes(permissoes, escopo, funcionario_id):
    service = AtividadeService(MagicMock())
    service.repository = MagicMock()
    service.repository.buscar_etapas.return_value = [
        EtapaKanban(etapa_id=2, nome="Em Execução", ordem=1),
        EtapaKanban(etapa_id=1, nome="Backlog", ordem=2),
    ]
    service.repository.buscar_atividades.return_value = [
        Atividade(
            atividade_id=3,
            titulo="Atividade",
            data_prazo=datetime(2026, 10, 30),
            etapa_id=1,
            processo_id=None,
        )
    ]
    service.repository.buscar_responsaveis.return_value = [(3, 7, "Responsável")]
    funcionario = Funcionario(
        atuacao_id=1, foto_perfil=1, funcionario_id=7, cargo=Cargo(permissao=permissoes)
    )

    resultado = service.visualizar_kanban(funcionario)

    assert resultado.escopo == escopo
    assert [etapa.etapa_id for etapa in resultado.etapas] == [2, 1]
    assert resultado.etapas[0].atividades == []
    cartao = resultado.etapas[1].atividades[0]
    assert cartao.atividade_id == 3
    assert cartao.responsaveis[0].model_dump() == {"funcionario_id": 7, "nome": "Responsável"}
    service.repository.buscar_atividades.assert_called_once_with(funcionario_id=funcionario_id)
    service.repository.buscar_responsaveis.assert_called_once_with([3])


@pytest.mark.parametrize(
    "contagens, progresso",
    [
        ((1, 1, 3, 3), 12.5),
        ((1, 0, 0, 0), 100.0),
        ((0, 0, 0, 0), 0.0),
        ((1, 1, 1, 0), 33.33),
    ],
)
def test_produtividade_calcula_progresso_e_usa_dia_local(contagens, progresso):
    service = AtividadeService(MagicMock())
    totais = dict(
        zip(("finalizadas", "a_fazer", "em_andamento", "atrasadas"), contagens, strict=True)
    )
    service.repository.buscar_produtividade_equipe = MagicMock(
        return_value=[{"funcionario_id": 7, "nome": "Responsável", **totais}]
    )
    with patch("app.atividade.service.datetime", wraps=datetime) as relogio:
        relogio.now.return_value = datetime(2026, 10, 22, 23, 30)
        resultado = service.visualizar_produtividade_equipe()

    relogio.now.assert_called_once_with(ZoneInfo("America/Sao_Paulo"))
    service.repository.buscar_produtividade_equipe.assert_called_once_with(datetime(2026, 10, 22))
    assert resultado[0].model_dump() == {
        "funcionario_id": 7,
        "nome": "Responsável",
        **totais,
        "progresso": progresso,
    }


def test_produtividade_retorna_equipe_vazia():
    service = AtividadeService(MagicMock())
    service.repository.buscar_produtividade_equipe = MagicMock(return_value=[])
    assert service.visualizar_produtividade_equipe() == []


@pytest.mark.parametrize(
    ("termo_busca", "qtd_esperada", "titulo_esperado"),
    [
        ("Elaborar Petição", 1, "Elaborar Petição Inicial"),
        ("Revisão", 1, "Revisão de Contrato"),
        ("InexistenteNoBanco", 0, None),
    ],
)
def test_buscar_atividades_com_filtros(
    db_session, atividades_para_filtro, termo_busca, qtd_esperada, titulo_esperado
):
    service = AtividadeService(db_session)

    filtro = AtividadeFilter.model_validate({"titulo": termo_busca})
    resultado = service.buscar_atividades(filtro)

    assert len(resultado) == qtd_esperada
    if qtd_esperada > 0:
        assert resultado[0].titulo == titulo_esperado


def test_buscar_atividades_apenas_minhas_usa_funcionario_do_usuario():
    service = AtividadeService(MagicMock())
    service.repository = MagicMock()
    service.repository.buscar_por_filtros.return_value = []

    usuario = Funcionario(atuacao_id=1, foto_perfil=1, funcionario_id=42)
    filtro = AtividadeFilter.model_validate({"apenas_minhas": True})

    service.buscar_atividades(filtro, usuario=usuario)

    _, kwargs = service.repository.buscar_por_filtros.call_args
    assert kwargs["funcionario_id"] == 42


def test_buscar_atividades_restringe_funcionario_id_de_outro_usuario():
    service = AtividadeService(MagicMock())
    service.repository = MagicMock()
    service.repository.buscar_por_filtros.return_value = []

    usuario = Funcionario(atuacao_id=1, foto_perfil=1, funcionario_id=42)
    filtro = AtividadeFilter.model_validate({"funcionario_id": 99})

    assert service.buscar_atividades(filtro, usuario=usuario) == []

    service.repository.buscar_por_filtros.assert_not_called()


def test_buscar_atividades_rejeita_apenas_minhas_com_funcionario_id():
    with pytest.raises(ValidationError):
        AtividadeFilter.model_validate({"apenas_minhas": True, "funcionario_id": 99})


@pytest.mark.parametrize(
    ("atividades_retornadas", "responsaveis_retornados", "qtd_esperada"),
    [
        ([], [], 0),
        (
            [
                Atividade(
                    atividade_id=10,
                    titulo="Atividade A",
                    descricao="Desc",
                    data_inicio=datetime(2026, 10, 1),
                    data_prazo=datetime(2026, 10, 30),
                    etapa_id=1,
                    processo_id=None,
                ),
                Atividade(
                    atividade_id=11,
                    titulo="Atividade B",
                    descricao="Desc",
                    data_inicio=datetime(2026, 10, 1),
                    data_prazo=datetime(2026, 10, 30),
                    etapa_id=1,
                    processo_id=None,
                ),
            ],
            [(10, 7, "Fulano"), (11, 7, "Fulano"), (11, 8, "Ciclano")],
            2,
        ),
    ],
)
def test_buscar_atividades_executa_consulta_e_mapeia_responsaveis(
    atividades_retornadas, responsaveis_retornados, qtd_esperada
):
    service = AtividadeService(MagicMock())
    service.repository = MagicMock()
    service.repository.buscar_por_filtros.return_value = atividades_retornadas
    service.repository.buscar_responsaveis.return_value = responsaveis_retornados

    usuario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        funcionario_id=99,
        cargo=Cargo(permissao={"gerenciar_equipe": True}),
    )
    filtro = AtividadeFilter.model_validate({})

    resultado = service.buscar_atividades(filtro, usuario=usuario)

    assert len(resultado) == qtd_esperada
    if qtd_esperada == 0:
        service.repository.buscar_responsaveis.assert_not_called()
    else:
        atv10 = next(r for r in resultado if r.atividade_id == 10)
        assert atv10.responsaveis == [ResponsavelKanbanResponse(funcionario_id=7, nome="Fulano")]
        atv11 = next(r for r in resultado if r.atividade_id == 11)
        assert len(atv11.responsaveis) == 2
        assert atv11.responsaveis[0].nome == "Fulano"
        assert atv11.responsaveis[1].nome == "Ciclano"
        service.repository.buscar_responsaveis.assert_called_once_with([10, 11])


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
