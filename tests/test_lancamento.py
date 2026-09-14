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


def test_atualizar_status_lancamento_entrada_atrasado():
    response = client.get("/lancamentos/")
    lancamento_id = response.json()[0]["lancamento_id"]

    payload = {"status": "Atrasado"}
    response = client.patch(f"/lancamentos/{lancamento_id}/status", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "Atrasado"


def test_atualizar_status_invalido():
    response = client.get("/lancamentos/")
    lancamento_id = response.json()[0]["lancamento_id"]

    payload = {"status": "Pago"}
    response = client.patch(f"/lancamentos/{lancamento_id}/status", json=payload)
    assert response.status_code == 400


def test_atualizar_status_lancamento_saida():
    payload = {
        "tipo": "Saída",
        "titulo": "Aluguel",
        "descricao": "Aluguel do escritório",
        "valor": 2000.0,
        "data_vencimento": "2026-10-10",
        "categoria": "escritorio",
    }
    response = client.post("/lancamentos/", json=payload)
    assert response.status_code == 201
    saida_id = response.json()["lancamento_id"]

    res_atrasado = client.patch(f"/lancamentos/{saida_id}/status", json={"status": "Atrasado"})
    assert res_atrasado.status_code == 200
    assert res_atrasado.json()["status"] == "Atrasado"

    res_pago = client.patch(f"/lancamentos/{saida_id}/status", json={"status": "Pago"})
    assert res_pago.status_code == 200
    assert res_pago.json()["status"] == "Pago"

    res_invalido = client.patch(f"/lancamentos/{saida_id}/status", json={"status": "Recebido"})
    assert res_invalido.status_code == 400

    client.delete(f"/lancamentos/{saida_id}")


def test_remover_lancamento():
    response = client.get("/lancamentos/")
    lancamento_id = response.json()[0]["lancamento_id"]

    response = client.delete(f"/lancamentos/{lancamento_id}")
    assert response.status_code == 204

    response = client.get("/lancamentos/")
    assert len(response.json()) == 0


def test_lancamento_nao_encontrado_e_tipo_invalido():
    res = client.put("/lancamentos/99999", json={"titulo": "Inexistente"})
    assert res.status_code == 404

    res = client.patch("/lancamentos/99999/status", json={"status": "Atrasado"})
    assert res.status_code == 404

    res = client.delete("/lancamentos/99999")
    assert res.status_code == 404

    payload = {
        "tipo": "Entrada",
        "titulo": "Teste Tipo",
        "valor": 100.0,
        "data_vencimento": "2026-10-10",
        "categoria": "outros",
    }
    create_res = client.post("/lancamentos/", json=payload)
    novo_id = create_res.json()["lancamento_id"]

    res_tipo = client.put(f"/lancamentos/{novo_id}", json={"tipo": "Invalido"})
    assert res_tipo.status_code == 400

    client.delete(f"/lancamentos/{novo_id}")
