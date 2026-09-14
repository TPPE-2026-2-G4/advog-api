from fastapi.testclient import TestClient

from app.config.database import Base, SessionLocal, engine
from app.models.lancamento import Lancamento
from main import app

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Lancamento).delete()
    db.commit()
    db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def test_criar_lancamento_entrada():
    payload = {
        "tipo": "Entrada",
        "titulo": "Honorários",
        "descricao": "Pagamento de honorários cliente X",
        "valor": 1500.0,
        "data_vencimento": "2026-10-15",
        "data_pagamento": "2026-10-15",
        "categoria": "honorarios",
        "status": "Pago",
        "recorrente": False,
    }
    response = client.post("/lancamentos/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["titulo"] == "Honorários"
    assert data["lancamento_id"] is not None


def test_criar_lancamento_tipo_invalido():
    payload = {
        "tipo": "Transferencia",
        "titulo": "Investimento",
        "valor": 500.0,
        "data_vencimento": "2026-10-15",
        "categoria": "outros",
    }
    response = client.post("/lancamentos/", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Tipo deve ser 'Entrada' ou 'Saída'"


def test_listar_lancamentos():
    response = client.get("/lancamentos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_atualizar_lancamento():
    response = client.get("/lancamentos/")
    lancamento_id = response.json()[0]["lancamento_id"]

    payload = {"titulo": "Honorários - Atualizado", "valor": 3000.0}
    response = client.put(f"/lancamentos/{lancamento_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["titulo"] == "Honorários - Atualizado"
    assert data["valor"] == 3000.0


def test_atualizar_status_lancamento_entrada():
    response = client.get("/lancamentos/")
    lancamento_id = response.json()[0]["lancamento_id"]

    payload = {"status": "Recebido"}
    response = client.patch(f"/lancamentos/{lancamento_id}/status", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "Recebido"


def test_atualizar_status_invalido():
    response = client.get("/lancamentos/")
    lancamento_id = response.json()[0]["lancamento_id"]

    # Lançamento do tipo Entrada não pode ter status "Pago"
    payload = {"status": "Pago"}
    response = client.patch(f"/lancamentos/{lancamento_id}/status", json=payload)
    assert response.status_code == 400


def test_remover_lancamento():
    response = client.get("/lancamentos/")
    lancamento_id = response.json()[0]["lancamento_id"]

    response = client.delete(f"/lancamentos/{lancamento_id}")
    assert response.status_code == 204

    response = client.get("/lancamentos/")
    assert len(response.json()) == 0
