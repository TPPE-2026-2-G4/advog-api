from datetime import datetime, timedelta

import pytest


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


def test_criar_lancamento_com_categoria(client, categoria):
    r = client.post("/lancamentos/", json=_payload(categoria_id=categoria["categoria_id"]))
    assert r.status_code == 201
    assert r.json()["situacao"] == "Previsto"
    assert r.json()["categoria_id"] == categoria["categoria_id"]


def test_criar_lancamento_tipo_invalido(client):
    assert client.post("/lancamentos/", json=_payload(tipo="x")).status_code == 422


def test_criar_lancamento_categoria_inexistente(client):
    r = client.post("/lancamentos/", json=_payload(categoria_id=999))
    assert r.status_code == 404


def test_criar_lancamento_cliente_inexistente(client):
    assert client.post("/lancamentos/", json=_payload(cliente_id=999)).status_code == 404


def test_status_incompativel_com_tipo(client):
    r = client.post("/lancamentos/", json=_payload(tipo="e", status="Pago"))
    assert r.status_code == 400


def test_atualizar_e_status(client):
    lid = client.post("/lancamentos/", json=_payload()).json()["lancamento_id"]
    r = client.put(f"/lancamentos/{lid}", json={"titulo": "Novo", "valor": 3000.0})
    assert r.status_code == 200 and r.json()["titulo"] == "Novo"
    r = client.patch(f"/lancamentos/{lid}/status", json={"status": "Recebido"})
    assert r.json()["situacao"] == "Realizado"
    r = client.patch(f"/lancamentos/{lid}/status", json={"status": "Pago"})
    assert r.status_code == 400


def test_remover_e_nao_encontrado(client):
    lid = client.post("/lancamentos/", json=_payload()).json()["lancamento_id"]
    assert client.delete(f"/lancamentos/{lid}").status_code == 204
    assert client.delete(f"/lancamentos/{lid}").status_code == 404


def _popular(client):
    agora = datetime.now()
    client.post("/lancamentos/", json=_payload(titulo="previsto", valor=100))
    client.post(
        "/lancamentos/",
        json=_payload(
            titulo="feito",
            tipo="s",
            status="Pago",
            valor=50,
            data_vencimento=(agora - timedelta(days=10)).isoformat(),
        ),
    )
    client.post(
        "/lancamentos/",
        json=_payload(
            titulo="atrasado",
            valor=200,
            data_vencimento=(agora - timedelta(days=3)).isoformat(),
        ),
    )


def test_filtrar_por_situacao(client):
    _popular(client)
    for situacao, titulo in [
        ("Previsto", "previsto"),
        ("Realizado", "feito"),
        ("Atrasado", "atrasado"),
    ]:
        itens = client.get("/lancamentos/", params={"situacao": situacao}).json()
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


def test_resumo(client):
    _popular(client)
    data = client.get("/lancamentos/resumo").json()
    assert data["previsto"] == {"quantidade": 1, "total_entradas": 100.0, "total_saidas": 0.0}
    assert data["realizado"] == {"quantidade": 1, "total_entradas": 0.0, "total_saidas": 50.0}
    assert data["atrasado"]["total_entradas"] == 200.0


def test_listar_paginado(client):
    _popular(client)
    r = client.get("/lancamentos/paginado", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3 and data["total_pages"] == 2
    assert [i["titulo"] for i in data["itens"]] == ["feito", "atrasado"]

    data = client.get("/lancamentos/paginado", params={"page": 2, "page_size": 2}).json()
    assert [i["titulo"] for i in data["itens"]] == ["previsto"]


def test_listar_paginado_com_filtros(client):
    _popular(client)
    data = client.get("/lancamentos/paginado", params={"situacao": "Atrasado"}).json()
    assert data["total"] == 1 and data["itens"][0]["titulo"] == "atrasado"
    vazio = client.get("/lancamentos/paginado", params={"tipo": "s", "situacao": "Previsto"}).json()
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
    assert client.patch("/lancamentos/1/status", json={"status": "Pago"}).status_code == 401
    assert client.delete("/lancamentos/1").status_code == 401
