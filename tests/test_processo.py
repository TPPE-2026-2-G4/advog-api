from fastapi.testclient import TestClient
from main import app
from app.config.database import Base, engine, SessionLocal
from app.models.processo_model import Processo

client = TestClient(app)

def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Processo).delete()
    
    p1 = Processo(
        id="0001", tribunal="tjsp", titulo="Caso Teste 1",
        cliente="João", area="civil", responsavel="alexandre", status="ativo", prazo="20/10/2026", diasRestantes=10
    )
    p2 = Processo(
        id="0002", tribunal="trt2", titulo="Caso Teste 2",
        cliente="Maria", area="trab", responsavel="ana", status="pendente", prazo="25/11/2026", diasRestantes=15
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
