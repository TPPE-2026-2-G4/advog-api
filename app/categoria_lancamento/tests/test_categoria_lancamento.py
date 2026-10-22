from datetime import datetime

import pytest


@pytest.fixture()
def client(client, token_admin):
    client.headers["Authorization"] = f"Bearer {token_admin}"
    return client


def test_crud_categoria(client):
    r = client.post("/categorias-lancamento", json={"nome_categoria": "Custas"})
    assert r.status_code == 201
    cid = r.json()["categoria_id"]

    assert (
        client.post("/categorias-lancamento", json={"nome_categoria": "Custas"}).status_code == 400
    )
    assert len(client.get("/categorias-lancamento").json()) == 1

    r = client.put(f"/categorias-lancamento/{cid}", json={"nome_categoria": "Taxas"})
    assert r.json()["nome_categoria"] == "Taxas"

    assert client.delete(f"/categorias-lancamento/{cid}").status_code == 200
    assert client.get(f"/categorias-lancamento/{cid}").status_code == 404


def test_nao_exclui_categoria_com_lancamentos(client):
    cid = client.post("/categorias-lancamento", json={"nome_categoria": "X"}).json()["categoria_id"]
    client.post(
        "/lancamentos/",
        json={
            "titulo": "t",
            "tipo": "s",
            "valor": 1,
            "categoria_id": cid,
            "data_vencimento": datetime.now().isoformat(),
        },
    )
    assert client.delete(f"/categorias-lancamento/{cid}").status_code == 400


def test_rotas_exigem_autenticacao(client):
    client.headers.pop("Authorization")
    assert client.get("/categorias-lancamento").status_code == 401
    assert client.get("/categorias-lancamento/1").status_code == 401
    assert client.post("/categorias-lancamento", json={"nome_categoria": "X"}).status_code == 401
    assert client.put("/categorias-lancamento/1", json={"nome_categoria": "X"}).status_code == 401
    assert client.delete("/categorias-lancamento/1").status_code == 401
