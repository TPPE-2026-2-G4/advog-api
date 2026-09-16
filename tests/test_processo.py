from fastapi.testclient import TestClient

from app.config.database import Base, SessionLocal, engine
from app.models.processo import Processo, StatusProcesso
from main import app

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Processo).delete()

    p1 = Processo(
        id="0061234-56.2026.8.26.0100",
        tribunal="tjsp",
        titulo="Caso Teste 1",
        cliente="João",
        area="civil",
        responsavel="alexandre",
        status=StatusProcesso.ATIVO,
        prazo="20/10/2026",
        diasRestantes=10,
    )
    p2 = Processo(
        id="0061235-56.2026.8.26.0100",
        tribunal="trt2",
        titulo="Caso Teste 2",
        cliente="Maria",
        area="trab",
        responsavel="ana",
        status=StatusProcesso.PENDENTE,
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
    response = client.get("/processos/?status=Ativo")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "Ativo"


def test_filtrar_processos_por_responsavel_e_area():
    response = client.get("/processos/?responsavel=ana&area=trab")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["cliente"] == "Maria"


def test_filtrar_processos_inexistente():
    response = client.get("/processos/?id=0061236-56.2026.8.26.0100")
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
        "id": "0061236-56.2026.8.26.0100",
        "titulo": "Caso Teste 3",
        "cliente": "Pedro",
        "status": "Ativo",
        "tribunal": "tjrj",
        "area": "penal",
        "responsavel": "carla",
        "prazo": "05/12/2026",
        "diasRestantes": 20,
    }
    response = client.post("/processos/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "0061236-56.2026.8.26.0100"
    assert data["cliente"] == "Pedro"

    response = client.get("/processos/?id=0061236-56.2026.8.26.0100")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_criar_processo_rejeita_id_fora_do_formato_cnj():
    payload = {
        "id": "0000000000000000000000001",
        "titulo": "Caso Inválido",
        "cliente": "Pedro",
        "status": "Ativo",
        "tribunal": "tjrj",
        "area": "penal",
        "responsavel": "carla",
        "prazo": "05/12/2026",
        "diasRestantes": 20,
    }

    response = client.post("/processos/", json=payload)

    assert response.status_code == 422
