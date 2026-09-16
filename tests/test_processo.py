from fastapi.testclient import TestClient

from app.config.database import Base, SessionLocal, engine
from app.models.processo import Processo
from main import app

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Processo).delete()

    p1 = Processo(
        cnj="1111111-11.2026.8.26.0000",
        titulo="Caso Teste 1",
        descricao="Descrição do caso 1",
        status="Ativo",
        tribunal="TJSP",
        area="Civil",
        data_inicio="2026-01-01",
        data_realizado="2026-01-10",
        data_prazo="2026-12-31",
        cliente_id=1,
    )
    p2 = Processo(
        cnj="2222222-22.2026.5.02.0000",
        titulo="Caso Teste 2",
        descricao="Descrição do caso 2",
        status="Pendente",
        tribunal="TRT2",
        area="Trabalhista",
        data_inicio="2026-02-01",
        data_realizado="2026-02-10",
        data_prazo="2026-11-30",
        cliente_id=2,
    )

    db.add(p1)
    db.add(p2)
    db.commit()
    db.refresh(p1)
    db.refresh(p2)
    module.p1_id = p1.processo_id
    module.p2_id = p2.processo_id
    db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Bem vindo a API de Gestão de Advocacia (FastAPI)"}


def test_filtrar_processos_sem_filtros():
    response = client.get("/processos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_filtrar_processos_por_status():
    response = client.get("/processos/?status=ativo")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "Ativo"


def test_filtrar_processos_por_area_e_cliente():
    response = client.get("/processos/?area=Trabalhista&cliente_id=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["cliente_id"] == 2


def test_filtrar_processos_inexistente():
    response = client.get("/processos/?processo_id=9999")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_filtrar_processos_por_tribunal():
    response = client.get("/processos/?tribunal=TRT2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tribunal"] == "TRT2"


def test_filtrar_processos_por_titulo():
    response = client.get("/processos/?titulo=Caso Teste 1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Caso Teste 1"


def test_filtrar_processos_por_cliente():
    response = client.get("/processos/?cliente_id=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["cliente_id"] == 2


def test_filtrar_processos_por_cnj():
    response = client.get("/processos/?cnj=1111111-11.2026.8.26.0000")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["cnj"] == "1111111-11.2026.8.26.0000"


def test_criar_processo():
    payload = {
        "cnj": "3333333-33.2026.4.03.0000",
        "titulo": "Caso Teste 3",
        "descricao": "Descrição do caso 3",
        "status": "Em Análise",
        "tribunal": "TRF3",
        "area": "Tributária",
        "data_inicio": "2026-03-01",
        "data_realizado": "2026-03-10",
        "data_prazo": "2026-10-31",
        "cliente_id": 3,
    }
    response = client.post("/processos/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "processo_id" in data
    assert data["cliente_id"] == 3
    assert data["cnj"] == "3333333-33.2026.4.03.0000"

    processo_id = data["processo_id"]
    response = client.get(f"/processos/?processo_id={processo_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
