import pytest


@pytest.mark.parametrize(
    "nome_cargo",
    [
        "Administrador",
        "Advogado",
        "Advogado Sênior",
        "Assistente Jurídico",
        "Estagiário",
    ],
)
def test_criar_cargo_retorna_cargo_criado(client, nome_cargo):
    response = client.post("/cargos", json={"nome_cargo": nome_cargo})
    assert response.status_code == 201
    assert response.json()["cargo_id"] is not None
    assert response.json()["nome_cargo"] == nome_cargo


def test_criar_cargo_com_nome_existente_retorna_erro(client):
    response = client.post("/cargos", json={"nome_cargo": "Advogado Sênior"})
    assert response.status_code == 201

    response_erro = client.post("/cargos", json={"nome_cargo": "Advogado Sênior"})
    assert response_erro.status_code == 400
    assert response_erro.json()["detail"] == "Cargo já cadastrado"


def test_buscar_todos_cargos_sem_cargos_cadastrados_retorna_lista_vazia(client):
    response = client.get("/cargos")
    assert response.status_code == 200
    assert response.json() == []
    assert isinstance(response.json(), list)


def test_buscar_todos_cargos_com_cargos_cadastrados_retorna_lista(client):
    response1 = client.post("/cargos", json={"nome_cargo": "Advogado Pleno"})
    assert response1.status_code == 201

    response2 = client.post("/cargos", json={"nome_cargo": "Consultor Jurídico"})
    assert response2.status_code == 201

    response = client.get("/cargos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2
    assert response.json()[0]["nome_cargo"] == "Advogado Pleno"
    assert response.json()[1]["nome_cargo"] == "Consultor Jurídico"
