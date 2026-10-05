from datetime import datetime

from fastapi.testclient import TestClient

from app.cliente.model import Cliente
from app.config.database import Base, SessionLocal, engine
from app.processo.model import Processo
from main import app

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Processo).delete()

    p1 = Processo(
        cnj="1111111-11.2026.8.26.0000",
        titulo_proc="Caso Teste 1",
        descricao_proc="Descrição do caso 1",
        status="Ativo",
        tribunal="TJSP",
        area="Civil",
        data_inicio=datetime(2026, 1, 1),
        data_realizado=datetime(2026, 1, 10),
        data_prazo=datetime(2026, 12, 31),
        cliente_id=1,
        responsavel_id=1,
    )
    p2 = Processo(
        cnj="2222222-22.2026.5.02.0000",
        titulo_proc="Caso Teste 2",
        descricao_proc="Descrição do caso 2",
        status="Pendente",
        tribunal="TRT2",
        area="Trabalhista",
        data_inicio=datetime(2026, 2, 1),
        data_realizado=datetime(2026, 2, 10),
        data_prazo=datetime(2026, 11, 30),
        cliente_id=2,
        responsavel_id=2,
    )

    db.add(
        Cliente(
            cliente_id=1,
            nome="Maria Oliveira",
            telefone="11999999999",
            email="maria.oliveira@teste.com",
            ultima_interacao=datetime(2026, 1, 1),
            etapa_id=1,
        )
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
    data = response.json()["itens"]
    assert len(data) == 2


def test_filtrar_processos_por_status():
    response = client.get("/processos/?status=ativo")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["status"] == "Ativo"


def test_filtrar_processos_por_area_e_cliente():
    response = client.get("/processos/?area=Trabalhista&cliente_id=2")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["cliente_id"] == 2


def test_filtrar_processos_inexistente():
    response = client.get("/processos/?processo_id=9999")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 0


def test_filtrar_processos_por_tribunal():
    response = client.get("/processos/?tribunal=TRT2")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["tribunal"] == "TRT2"


def test_filtrar_processos_por_titulo():
    response = client.get("/processos/?titulo_proc=Caso Teste 1")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["titulo_proc"] == "Caso Teste 1"


def test_filtrar_processos_por_cliente():
    response = client.get("/processos/?cliente_id=2")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["cliente_id"] == 2


def test_filtrar_processos_por_cnj():
    response = client.get("/processos/?cnj=1111111-11.2026.8.26.0000")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["cnj"] == "1111111-11.2026.8.26.0000"


def test_filtrar_processos_por_responsavel():
    response = client.get("/processos/?responsavel_id=1")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["responsavel_id"] == 1


def test_criar_processo():
    payload = {
        "cnj": "3333333-33.2026.4.03.0000",
        "titulo_proc": "Caso Teste 3",
        "descricao_proc": "Descrição do caso 3",
        "status": "Em Análise",
        "tribunal": "TRF3",
        "area": "Tributária",
        "data_inicio": "2026-03-01T00:00:00",
        "data_realizado": "2026-03-10T00:00:00",
        "data_prazo": "2026-10-31T00:00:00",
        "cliente_id": 3,
        "responsavel_id": 1,
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
    assert response.json()["total"] == 1


def test_buscar_processos_por_numero_cnj_ou_titulo():
    response = client.get("/processos/?busca=2222222-22")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["cnj"] == "2222222-22.2026.5.02.0000"

    response = client.get("/processos/?busca=caso teste 1")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["titulo_proc"] == "Caso Teste 1"


def test_buscar_processos_pelo_nome_do_cliente():
    response = client.get("/processos/?busca=maria oliveira")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["cliente_id"] == 1

    response = client.get("/processos/?busca=inexistente")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_filtrar_processos_por_intervalo_de_prazo_inclusivo():
    response = client.get("/processos/?prazo_inicio=2026-11-01&prazo_fim=2026-11-30")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["titulo_proc"] == "Caso Teste 2"

    response = client.get("/processos/?prazo_inicio=2026-10-31&prazo_fim=2026-10-31")
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["cnj"] == "3333333-33.2026.4.03.0000"


def test_filtrar_processos_combinando_busca_status_responsavel_e_prazo():
    response = client.get(
        "/processos/?busca=Caso&status=ativo&responsavel_id=1"
        "&prazo_inicio=2026-01-01&prazo_fim=2026-12-31"
    )
    assert response.status_code == 200
    data = response.json()["itens"]
    assert len(data) == 1
    assert data[0]["titulo_proc"] == "Caso Teste 1"


def test_listar_processos_paginados_retorna_metadados_de_paginacao():
    response = client.get("/processos/?page=1&page_size=2")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] >= 2
    assert len(body["itens"]) == 2
    assert body["total_pages"] == -(-body["total"] // 2)


def test_listar_processos_pagina_alem_do_fim_retorna_lista_vazia():
    total = client.get("/processos/").json()["total"]

    response = client.get("/processos/?page=1000&page_size=5")
    assert response.status_code == 200
    body = response.json()
    assert body["itens"] == []
    assert body["total"] == total


def test_listar_processos_rejeita_parametros_de_paginacao_invalidos():
    assert client.get("/processos/?page=0").status_code == 422
    assert client.get("/processos/?page_size=0").status_code == 422
    assert client.get("/processos/?page_size=101").status_code == 422
