from datetime import datetime

from fastapi.testclient import TestClient

from app.cliente.model import Cliente
from app.config.database import Base, SessionLocal, engine
from app.core.dependencies import obter_funcionario_atual
from main import app

Base.metadata.create_all(bind=engine)


def override_obter_funcionario_atual():
    return {"id": 1, "email": "test@test.com"}


client = TestClient(app)


def setup_function():
    app.dependency_overrides[obter_funcionario_atual] = override_obter_funcionario_atual
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Cliente).delete()
    db.commit()

    c1 = Cliente(
        nome="Cliente Teste 1",
        telefone="(11) 91111-1111",
        email="cliente1@teste.com",
        area_interesse="Civil",
        ultima_interacao=datetime(2026, 1, 1),
        responsavel_id=1,
        etapa_id=1,
    )
    c2 = Cliente(
        nome="Cliente Teste 2",
        telefone="(22) 92222-2222",
        email="cliente2@teste.com",
        area_interesse="Trabalhista",
        ultima_interacao=datetime(2026, 2, 1),
        responsavel_id=2,
        etapa_id=2,
    )

    db.add(c1)
    db.add(c2)
    db.commit()
    db.close()


def teardown_function():
    app.dependency_overrides.clear()
    db = SessionLocal()
    db.query(Cliente).delete()
    db.commit()
    db.close()


def test_listar_clientes():
    response = client.get("/clientes/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_filtrar_clientes_por_busca_nome():
    response = client.get("/clientes/?busca=Teste 1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nome"] == "Cliente Teste 1"


def test_filtrar_clientes_por_busca_email():
    response = client.get("/clientes/?busca=cliente2@teste.com")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == "cliente2@teste.com"


def test_filtrar_clientes_por_responsavel():
    response = client.get("/clientes/?responsavel_id=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["responsavel_id"] == 2


def test_filtrar_clientes_por_etapa():
    response = client.get("/clientes/?etapa_id=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["etapa_id"] == 1


def test_criar_cliente():
    payload = {
        "nome": "Novo Cliente 3",
        "telefone": "(33) 93333-3333",
        "email": "novo@teste.com",
        "area_interesse": "Tributário",
        "ultima_interacao": "2026-03-01T00:00:00",
        "responsavel_id": 1,
        "etapa_id": 1,
    }
    response = client.post("/clientes/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Novo Cliente 3"
    assert data["cliente_id"] is not None


def test_obter_cliente_por_id():
    response = client.get("/clientes/")
    data = response.json()
    cliente_id = data[0]["cliente_id"]

    response2 = client.get(f"/clientes/{cliente_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cliente_id"] == cliente_id
    assert data2["nome"] == data[0]["nome"]


def test_obter_cliente_inexistente():
    response = client.get("/clientes/999999")
    assert response.status_code == 404
