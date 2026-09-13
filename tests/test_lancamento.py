from fastapi.testclient import TestClient
from main import app
from app.config.database import Base, engine, SessionLocal
from app.models.lancamento import Lancamento

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
        "data": "2026-10-15",
        "categoria": "honorarios",
        "status": "Pago",
        "recorrente": False
    }
    response = client.post("/lancamentos/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["titulo"] == "Honorários"
    assert data["id"] is not None

def test_criar_lancamento_tipo_invalido():
    payload = {
        "tipo": "Transferencia",
        "titulo": "Investimento",
        "valor": 500.0,
        "data": "2026-10-15",
        "categoria": "outros"
    }
    response = client.post("/lancamentos/", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Tipo deve ser 'Entrada' ou 'Saída'"

def test_listar_lancamentos():
    response = client.get("/lancamentos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
