from fastapi.testclient import TestClient

from app.config.database import Base, SessionLocal, engine
from app.models.processo_model import Processo
from main import app

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Processo).delete()

    p1 = Processo(
        id="0001",
        tribunal="tjsp",
        titulo="Caso Teste 1",
        cliente="João",
        area="civil",
        responsavel="alexandre",
        status="ativo",
        prazo="20/10/2026",
        diasRestantes=10,
    )
    p2 = Processo(
        id="0002",
        tribunal="trt2",
        titulo="Caso Teste 2",
        cliente="Maria",
        area="trab",
        responsavel="ana",
        status="pendente",
        prazo="25/11/2026",
        diasRestantes=15,
    )

    db.add(p1)
    db.add(p2)
    db.commit()
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
    assert data[0]["status"] == "ativo"


def test_filtrar_processos_por_responsavel_e_area():
    response = client.get("/processos/?responsavel=ana&area=trab")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["cliente"] == "Maria"


def test_filtrar_processos_inexistente():
    response = client.get("/processos/?id=9999")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_filtrar_processos_por_tribunal():
    response = client.get("/processos/?tribunal=trt2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tribunal"] == "trt2"


def test_filtrar_processos_por_titulo():
    response = client.get("/processos/?titulo=Caso Teste 1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Caso Teste 1"


def test_filtrar_processos_por_cliente():
    response = client.get("/processos/?cliente=Maria")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["cliente"] == "Maria"


def test_filtrar_processos_por_prazo():
    response = client.get("/processos/?prazo=20/10/2026")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["prazo"] == "20/10/2026"


def test_criar_processo():
    payload = {
        "id": "0003",
        "titulo": "Caso Teste 3",
        "cliente": "Pedro",
        "status": "ativo",
        "tribunal": "tjrj",
        "area": "penal",
        "responsavel": "carla",
        "prazo": "05/12/2026",
        "diasRestantes": 20,
    }
    response = client.post("/processos/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "0003"
    assert data["cliente"] == "Pedro"

    response = client.get("/processos/?id=0003")
    assert response.status_code == 200
    assert len(response.json()) == 1
