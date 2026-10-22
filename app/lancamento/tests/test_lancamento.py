from datetime import datetime, timedelta

import pytest

from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento


@pytest.fixture()
def client(client, token_admin):
    client.headers["Authorization"] = f"Bearer {token_admin}"
    return client


def _payload(**kwargs):
    base = {
        "titulo": "Honorários",
        "tipo": "e",
        "valor": 1000.0,
        "data_vencimento": (datetime.now() + timedelta(days=5)).isoformat(),
    }
    return {**base, **kwargs}


@pytest.fixture()
def categoria(client):
    return client.post("/categorias-lancamento", json={"nome_categoria": "Honorários"}).json()


def _criar(client, **kwargs):
    r = client.post("/lancamentos/", json=_payload(**kwargs))
    assert r.status_code == 201
    return r.json()


def _dias(n):
    return (datetime.now() + timedelta(days=n)).isoformat()


def test_criar_lancamento_com_categoria(client, categoria):
    r = client.post("/lancamentos/", json=_payload(categoria_id=categoria["categoria_id"]))
    assert r.status_code == 201
    assert r.json()["status"] == "Pendente"
    assert r.json()["data_pagamento"] is None
    assert r.json()["categoria_id"] == categoria["categoria_id"]


def test_status_na_criacao_depende_do_vencimento(client):
    assert _criar(client, data_vencimento=_dias(1))["status"] == "Pendente"
    assert _criar(client, data_vencimento=datetime.now().isoformat())["status"] == "Pendente"
    assert _criar(client, data_vencimento=_dias(-1))["status"] == "Atrasado"


def test_status_enviado_pelo_cliente_e_ignorado(client):
    assert _criar(client, status="Realizado")["status"] == "Pendente"


def test_criar_lancamento_tipo_invalido(client):
    assert client.post("/lancamentos/", json=_payload(tipo="x")).status_code == 422


def test_criar_lancamento_categoria_inexistente(client):
    assert client.post("/lancamentos/", json=_payload(categoria_id=999)).status_code == 404


def test_criar_lancamento_cliente_inexistente(client):
    assert client.post("/lancamentos/", json=_payload(cliente_id=999)).status_code == 404


def test_atualizar_lancamento(client):
    lid = _criar(client)["lancamento_id"]
    r = client.put(f"/lancamentos/{lid}", json={"titulo": "Novo", "valor": 3000.0})
    assert r.status_code == 200 and r.json()["titulo"] == "Novo"
    assert r.json()["status"] == "Pendente"


def test_atualizar_campo_obrigatorio_nulo(client):
    lid = _criar(client)["lancamento_id"]
    assert client.put(f"/lancamentos/{lid}", json={"titulo": None}).status_code == 400


def test_atualizar_nao_encontrado(client):
    assert client.put("/lancamentos/999", json={"titulo": "x"}).status_code == 404


def test_atualizar_vencimento_reavalia_status(client):
    lid = _criar(client)["lancamento_id"]
    r = client.put(f"/lancamentos/{lid}", json={"data_vencimento": _dias(-2)})
    assert r.json()["status"] == "Atrasado"
    r = client.put(f"/lancamentos/{lid}", json={"data_vencimento": _dias(3)})
    assert r.json()["status"] == "Pendente"


def test_atualizar_vencimento_nao_altera_realizado(client):
    lid = _criar(client)["lancamento_id"]
    client.patch(f"/lancamentos/{lid}/alternar-status")
    r = client.put(f"/lancamentos/{lid}", json={"data_vencimento": _dias(-5)})
    assert r.json()["status"] == "Realizado"


def test_atualizar_ignora_status_manual(client):
    lid = _criar(client)["lancamento_id"]
    r = client.put(f"/lancamentos/{lid}", json={"status": "Realizado"})
    assert r.json()["status"] == "Pendente"


def test_alternar_status_pendente(client):
    lid = _criar(client)["lancamento_id"]
    r = client.patch(f"/lancamentos/{lid}/alternar-status")
    assert r.status_code == 200
    assert r.json()["status"] == "Realizado"
    assert r.json()["data_pagamento"] is not None
    r = client.patch(f"/lancamentos/{lid}/alternar-status")
    assert r.json()["status"] == "Pendente"
    assert r.json()["data_pagamento"] is None


def test_alternar_status_volta_para_atrasado(client):
    lid = _criar(client, data_vencimento=_dias(-3))["lancamento_id"]
    assert client.patch(f"/lancamentos/{lid}/alternar-status").json()["status"] == "Realizado"
    assert client.patch(f"/lancamentos/{lid}/alternar-status").json()["status"] == "Atrasado"


def test_alternar_status_nao_encontrado(client):
    assert client.patch("/lancamentos/999/alternar-status").status_code == 404


def test_rota_de_status_manual_removida(client):
    lid = _criar(client)["lancamento_id"]
    r = client.patch(f"/lancamentos/{lid}/status", json={"status": "Realizado"})
    assert r.status_code in (404, 405)


def test_pendente_vencido_vira_atrasado_automaticamente(client, db_session):
    db_session.add(
        Lancamento(
            titulo="Antigo",
            tipo=TipoLancamento.SAIDA,
            valor=10,
            status=StatusLancamento.PENDENTE,
            data_vencimento=datetime.now() - timedelta(days=2),
        )
    )
    db_session.commit()
    itens = client.get("/lancamentos/").json()
    assert [i["status"] for i in itens] == ["Atrasado"]


def test_remover_e_nao_encontrado(client):
    lid = _criar(client)["lancamento_id"]
    assert client.delete(f"/lancamentos/{lid}").status_code == 204
    assert client.delete(f"/lancamentos/{lid}").status_code == 404


def _popular(client):
    _criar(client, titulo="pendente", valor=100)
    feito = _criar(client, titulo="feito", tipo="s", valor=50, data_vencimento=_dias(-10))
    client.patch(f"/lancamentos/{feito['lancamento_id']}/alternar-status")
    _criar(client, titulo="atrasado", valor=200, data_vencimento=_dias(-3))


def test_filtrar_por_status(client):
    _popular(client)
    for status, titulo in [
        ("Pendente", "pendente"),
        ("Realizado", "feito"),
        ("Atrasado", "atrasado"),
    ]:
        itens = client.get("/lancamentos/", params={"status": status}).json()
        assert [i["titulo"] for i in itens] == [titulo]


def test_filtrar_por_periodo(client):
    _popular(client)
    hoje = datetime.now().date()
    r = client.get(
        "/lancamentos/",
        params={"inicio": (hoje - timedelta(days=5)).isoformat(), "fim": hoje.isoformat()},
    )
    assert [i["titulo"] for i in r.json()] == ["atrasado"]


@pytest.mark.parametrize(
    ("rota", "params"),
    [
        ("/lancamentos/", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
        ("/lancamentos/resumo", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
        ("/lancamentos/grafico", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
        ("/lancamentos/grafico", {"valor_min": 500.0, "valor_max": 100.0}),
    ],
)
def test_filtros_intervalo_invalido_retornam_400(client, rota, params):
    r = client.get(rota, params=params)
    assert r.status_code == 400


def test_resumo(client):
    _popular(client)
    data = client.get("/lancamentos/resumo").json()
    assert data["pendente"] == {"quantidade": 1, "total_entradas": 100.0, "total_saidas": 0.0}
    assert data["realizado"] == {"quantidade": 1, "total_entradas": 0.0, "total_saidas": 50.0}
    assert data["atrasado"] == {"quantidade": 1, "total_entradas": 200.0, "total_saidas": 0.0}


def test_grafico_agrupado_por_dia_e_tipo(client):
    dia_1 = _dias(-3)
    dia_2 = _dias(-1)
    _criar(client, titulo="entrada 1", tipo="e", valor=500.0, data_vencimento=dia_1)
    _criar(client, titulo="saida 1", tipo="s", valor=150.0, data_vencimento=dia_1)
    _criar(client, titulo="entrada 2", tipo="e", valor=300.0, data_vencimento=dia_2)

    r = client.get("/lancamentos/grafico")
    assert r.status_code == 200
    data = r.json()
    assert data["total_entradas"] == 800.0
    assert data["total_saidas"] == 150.0
    assert data["saldo"] == 650.0
    assert data["itens"] == [
        {
            "data": dia_1[:10],
            "quantidade": 2,
            "total_entradas": 500.0,
            "total_saidas": 150.0,
            "saldo": 350.0,
        },
        {
            "data": dia_2[:10],
            "quantidade": 1,
            "total_entradas": 300.0,
            "total_saidas": 0.0,
            "saldo": 300.0,
        },
    ]


@pytest.mark.parametrize(
    ("dias", "offset_fim", "entradas_esperadas", "saidas_esperadas", "saldo_esperado", "qtd_dias"),
    [
        (5, 0, 200.0, 0.0, 200.0, 1),
        (15, 0, 200.0, 50.0, 150.0, 2),
        (3, -2, 200.0, 0.0, 200.0, 1),
        (1, 0, 0.0, 0.0, 0.0, 0),
    ],
)
def test_grafico_filtrar_por_dias_parametrizado(
    client, dias, offset_fim, entradas_esperadas, saidas_esperadas, saldo_esperado, qtd_dias
):
    _popular(client)
    hoje = datetime.now().date()
    fim_esperado = hoje + timedelta(days=offset_fim)
    inicio_esperado = fim_esperado - timedelta(days=dias - 1)

    params = {"dias": dias}
    if offset_fim != 0:
        params["fim"] = fim_esperado.isoformat()

    r = client.get("/lancamentos/grafico", params=params)
    assert r.status_code == 200
    data = r.json()
    assert data["inicio"] == inicio_esperado.isoformat()
    assert data["fim"] == fim_esperado.isoformat()
    assert data["total_entradas"] == entradas_esperadas
    assert data["total_saidas"] == saidas_esperadas
    assert data["saldo"] == saldo_esperado
    assert len(data["itens"]) == qtd_dias


@pytest.mark.parametrize(
    (
        "valor_min",
        "valor_max",
        "entradas_esperadas",
        "saidas_esperadas",
        "saldo_esperado",
        "qtd_dias",
    ),
    [
        (80.0, 150.0, 100.0, 0.0, 100.0, 1),
        (0.0, 60.0, 0.0, 50.0, -50.0, 1),
        (50.0, 200.0, 300.0, 50.0, 250.0, 3),
        (500.0, 1000.0, 0.0, 0.0, 0.0, 0),
    ],
)
def test_grafico_filtrar_por_valores_parametrizado(
    client, valor_min, valor_max, entradas_esperadas, saidas_esperadas, saldo_esperado, qtd_dias
):
    _popular(client)
    r = client.get(
        "/lancamentos/grafico",
        params={"valor_min": valor_min, "valor_max": valor_max},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["valor_min"] == valor_min
    assert data["valor_max"] == valor_max
    assert data["total_entradas"] == entradas_esperadas
    assert data["total_saidas"] == saidas_esperadas
    assert data["saldo"] == saldo_esperado
    assert len(data["itens"]) == qtd_dias


def test_grafico_filtrar_por_categoria_e_cliente(client, categoria):
    _popular(client)
    _criar(client, titulo="cat", valor=120.0, categoria_id=categoria["categoria_id"])
    r = client.get(
        "/lancamentos/grafico",
        params={"categoria_id": categoria["categoria_id"]},
    )
    assert r.status_code == 200
    assert r.json()["total_entradas"] == 120.0
    assert client.get("/lancamentos/grafico", params={"cliente_id": 999}).json()["itens"] == []


@pytest.mark.parametrize(
    "params",
    [
        {"dias": 0},
        {"dias": -3},
        {"valor_min": -1.0},
        {"valor_max": -0.01},
    ],
)
def test_grafico_parametros_invalidos_retornam_422(client, params):
    assert client.get("/lancamentos/grafico", params=params).status_code == 422


def test_listar_paginado(client):
    _popular(client)
    r = client.get("/lancamentos/paginado", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3 and data["total_pages"] == 2
    assert [i["titulo"] for i in data["itens"]] == ["feito", "atrasado"]

    data = client.get("/lancamentos/paginado", params={"page": 2, "page_size": 2}).json()
    assert [i["titulo"] for i in data["itens"]] == ["pendente"]


def test_listar_paginado_com_filtros(client):
    _popular(client)
    data = client.get("/lancamentos/paginado", params={"status": "Atrasado"}).json()
    assert data["total"] == 1 and data["itens"][0]["titulo"] == "atrasado"
    vazio = client.get("/lancamentos/paginado", params={"tipo": "s", "status": "Pendente"}).json()
    assert vazio == {"itens": [], "total": 0, "page": 1, "page_size": 10, "total_pages": 1}


def test_listar_paginado_validacoes(client):
    assert client.get("/lancamentos/paginado", params={"page": 0}).status_code == 422
    assert client.get("/lancamentos/paginado", params={"page_size": 101}).status_code == 422
    r = client.get("/lancamentos/paginado", params={"inicio": "2026-10-10", "fim": "2026-10-01"})
    assert r.status_code == 400


def test_rotas_exigem_autenticacao(client):
    client.headers.pop("Authorization")
    assert client.get("/lancamentos/").status_code == 401
    assert client.get("/lancamentos/resumo").status_code == 401
    assert client.get("/lancamentos/grafico").status_code == 401
    assert client.get("/lancamentos/paginado").status_code == 401
    assert client.post("/lancamentos/", json=_payload()).status_code == 401
    assert client.put("/lancamentos/1", json={}).status_code == 401
    assert client.patch("/lancamentos/1/alternar-status").status_code == 401
    assert client.delete("/lancamentos/1").status_code == 401
