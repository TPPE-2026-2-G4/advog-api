from datetime import datetime

from fastapi.testclient import TestClient

from app.cliente.model import Cliente
from app.cliente.repository import ClienteRepository
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


def test_atualizar_cliente_sucesso():
    db = SessionLocal()
    repositorio = ClienteRepository(db)
    cliente = db.query(Cliente).first()
    assert cliente is not None

    dados_atualizacao = {"nome": "Cliente Teste Alterado", "telefone": "(11) 98888-8888"}
    cliente_atualizado = repositorio.update(cliente.cliente_id, dados_atualizacao)

    assert cliente_atualizado is not None
    assert cliente_atualizado.nome == "Cliente Teste Alterado"
    assert cliente_atualizado.telefone == "(11) 98888-8888"
    db.close()


def test_atualizar_cliente_inexistente_retorna_none():
    db = SessionLocal()
    repositorio = ClienteRepository(db)
    resultado = repositorio.update(99999, {"nome": "Inexistente"})

    assert resultado is None
    db.close()


def test_deletar_cliente_sucesso():
    db = SessionLocal()
    repositorio = ClienteRepository(db)
    cliente = db.query(Cliente).first()
    assert cliente is not None

    sucesso = repositorio.delete(cliente.cliente_id)
    cliente_buscado = repositorio.get_by_id(cliente.cliente_id)

    assert sucesso is True
    assert cliente_buscado is None
    db.close()


def test_deletar_cliente_inexistente_retorna_false():
    db = SessionLocal()
    repositorio = ClienteRepository(db)
    sucesso = repositorio.delete(99999)

    assert sucesso is False
    db.close()
