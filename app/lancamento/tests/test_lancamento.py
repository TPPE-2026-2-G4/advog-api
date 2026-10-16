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


def test_periodo_invalido(client):
    r = client.get("/lancamentos/", params={"inicio": "2026-10-10", "fim": "2026-10-01"})
    assert r.status_code == 400
    r = client.get("/lancamentos/resumo", params={"inicio": "2026-10-10", "fim": "2026-10-01"})
    assert r.status_code == 400


def test_resumo(client):
    _popular(client)
    data = client.get("/lancamentos/resumo").json()
    assert data["pendente"] == {"quantidade": 1, "total_entradas": 100.0, "total_saidas": 0.0}
    assert data["realizado"] == {"quantidade": 1, "total_entradas": 0.0, "total_saidas": 50.0}
    assert data["atrasado"] == {"quantidade": 1, "total_entradas": 200.0, "total_saidas": 0.0}


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
    assert client.get("/lancamentos/paginado").status_code == 401
    assert client.post("/lancamentos/", json=_payload()).status_code == 401
    assert client.put("/lancamentos/1", json={}).status_code == 401
    assert client.patch("/lancamentos/1/alternar-status").status_code == 401
    assert client.delete("/lancamentos/1").status_code == 401
