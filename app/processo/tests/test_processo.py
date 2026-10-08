from datetime import datetime

from fastapi.testclient import TestClient

from app.cargo.model import Cargo
from app.cliente.model import Cliente
from app.config.database import Base, SessionLocal, engine
from app.core.seguranca import criar_token_acesso
from app.funcionario.model import Funcionario, StatusFuncionario
from app.processo.model import Processo
from main import app

client = TestClient(app)

auth_headers: dict[str, str] = {}


def setup_module(module):
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    db.query(Processo).delete()

    cargo = Cargo(
        nome_cargo="Cargo de Teste de Processos",
        descricao="Cargo autorizado para os testes de processos",
        permissao={
            "visualizar_processos": True,
            "criar_processos": True,
        },
    )
    db.add(cargo)
    db.commit()
    db.refresh(cargo)

    funcionario1 = Funcionario(
        nome="Funcionário 1 de Testes",
        email="funcionario1.processo@test.com",
        status=StatusFuncionario.ATIVO,
        cargo_id=cargo.cargo_id,
    )

    funcionario2 = Funcionario(
        nome="Funcionário 2 de Testes",
        email="funcionario2.processo@test.com",
        status=StatusFuncionario.ATIVO,
        cargo_id=cargo.cargo_id,
    )

    db.add_all([funcionario1, funcionario2])
    db.commit()
    db.refresh(funcionario1)
    db.refresh(funcionario2)

    module.funcionario1_id = funcionario1.funcionario_id
    module.funcionario2_id = funcionario2.funcionario_id

    module.auth_headers = {
        "Authorization": (
            f"Bearer {criar_token_acesso({'sub': str(funcionario1.funcionario_id), 'email': funcionario1.email})}"
        )
    }

    cliente1 = Cliente(
        nome="Maria Oliveira",
        telefone="11999999999",
        email="maria.oliveira@teste.com",
        ultima_interacao=datetime(2026, 1, 1),
        etapa_id=1,
    )

    cliente2 = Cliente(
        nome="João Silva",
        telefone="11988888888",
        email="joao.silva@teste.com",
        ultima_interacao=datetime(2026, 1, 2),
        etapa_id=1,
    )

    cliente3 = Cliente(
        nome="Ana Souza",
        telefone="11977777777",
        email="ana.souza@teste.com",
        ultima_interacao=datetime(2026, 1, 3),
        etapa_id=1,
    )

    db.add_all([cliente1, cliente2, cliente3])
    db.commit()

    db.refresh(cliente1)
    db.refresh(cliente2)
    db.refresh(cliente3)

    module.cliente1_id = cliente1.cliente_id
    module.cliente2_id = cliente2.cliente_id
    module.cliente3_id = cliente3.cliente_id

    p1 = Processo(
        cnj="1111111-11.2026.8.26.0000",
        titulo="Caso Teste 1",
        descricao="Descrição do caso 1",
        status="Ativo",
        tribunal="TJSP",
        area="Civil",
        data_inicio=datetime(2026, 1, 1),
        data_realizado=datetime(2026, 1, 10),
        data_prazo=datetime(2026, 12, 31),
        cliente_id=cliente1.cliente_id,
        funcionario_id=funcionario1.funcionario_id,
    )

    p2 = Processo(
        cnj="2222222-22.2026.5.02.0000",
        titulo="Caso Teste 2",
        descricao="Descrição do caso 2",
        status="Em Análise",
        tribunal="TRT2",
        area="Trabalhista",
        data_inicio=datetime(2026, 2, 1),
        data_realizado=datetime(2026, 2, 10),
        data_prazo=datetime(2026, 11, 30),
        cliente_id=cliente2.cliente_id,
        funcionario_id=funcionario2.funcionario_id,
    )

    db.add_all([p1, p2])
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
    assert response.json() == {
        "message": "Bem vindo a API de Gestão de Advocacia (FastAPI)"
    }


def test_filtrar_processos_sem_filtros():
    response = client.get("/processos/", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    assert len(data["itens"]) == 2
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1


def test_filtrar_processos_por_status():
    response = client.get(
        "/processos/?status=Ativo",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["status"] == "Ativo"


def test_filtrar_processos_por_area_e_cliente():
    response = client.get(
        f"/processos/?area=Trabalhista&cliente_id={cliente2_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["cliente_id"] == cliente2_id


def test_filtrar_processos_inexistente():
    response = client.get(
        "/processos/?processo_id=999999",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["itens"] == []
    assert data["total"] == 0


def test_filtrar_processos_por_tribunal():
    response = client.get(
        "/processos/?tribunal=TRT2",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["tribunal"] == "TRT2"


def test_filtrar_processos_por_titulo():
    response = client.get(
        "/processos/?titulo=Caso Teste 1",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["titulo"] == "Caso Teste 1"


def test_filtrar_processos_por_cliente():
    response = client.get(
        f"/processos/?cliente_id={cliente2_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["cliente_id"] == cliente2_id


def test_filtrar_processos_por_cnj():
    response = client.get(
        "/processos/?cnj=1111111-11.2026.8.26.0000",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["cnj"] == "1111111-11.2026.8.26.0000"


def test_filtrar_processos_por_funcionario():
    response = client.get(
        f"/processos/?funcionario_id={funcionario1_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["funcionario_id"] == funcionario1_id


def test_criar_processo():
    payload = {
        "cnj": "3333333-33.2026.4.03.0000",
        "titulo": "Caso Teste 3",
        "descricao": "Descrição do caso 3",
        "status": "Em Análise",
        "tribunal": "TRF3",
        "area": "Tributária",
        "data_inicio": "2026-03-01T00:00:00",
        "data_realizado": "2026-03-10T00:00:00",
        "data_prazo": "2026-10-31T00:00:00",
        "cliente_id": cliente3_id,
        "funcionario_id": funcionario1_id,
    }

    response = client.post(
        "/processos/",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert "processo_id" in data
    assert data["cliente_id"] == cliente3_id
    assert data["funcionario_id"] == funcionario1_id
    assert data["cnj"] == "3333333-33.2026.4.03.0000"
    assert data["titulo"] == "Caso Teste 3"

    processo_id = data["processo_id"]

    response = client.get(
        f"/processos/?processo_id={processo_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_buscar_processos_por_numero_cnj_ou_titulo():
    response = client.get(
        "/processos/?busca=2222222-22",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["cnj"] == "2222222-22.2026.5.02.0000"

    response = client.get(
        "/processos/?busca=caso teste 1",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["titulo"] == "Caso Teste 1"


def test_buscar_processos_pelo_nome_do_cliente():
    response = client.get(
        "/processos/?busca=maria oliveira",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["cliente_id"] == cliente1_id

    response = client.get(
        "/processos/?busca=inexistente",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_filtrar_processos_por_intervalo_de_prazo_inclusivo():
    response = client.get(
        "/processos/?prazo_inicio=2026-11-01&prazo_fim=2026-11-30",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["titulo"] == "Caso Teste 2"

    response = client.get(
        "/processos/?prazo_inicio=2026-12-31&prazo_fim=2026-12-31",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["cnj"] == "1111111-11.2026.8.26.0000"


def test_filtrar_processos_combinando_busca_status_funcionario_e_prazo():
    response = client.get(
        "/processos/?busca=Caso&status=Ativo"
        f"&funcionario_id={funcionario1_id}"
        "&prazo_inicio=2026-01-01&prazo_fim=2026-12-31",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()["itens"]

    assert len(data) == 1
    assert data[0]["titulo"] == "Caso Teste 1"


def test_listar_processos_paginados_retorna_metadados_de_paginacao():
    response = client.get(
        "/processos/?page=1&page_size=2",
        headers=auth_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] == 2
    assert len(body["itens"]) == 2
    assert body["total_pages"] == 1


def test_listar_processos_pagina_alem_do_fim_retorna_lista_vazia():
    total = client.get(
        "/processos/",
        headers=auth_headers,
    ).json()["total"]

    response = client.get(
        "/processos/?page=1000&page_size=5",
        headers=auth_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["itens"] == []
    assert body["total"] == total


def test_listar_processos_rejeita_parametros_de_paginacao_invalidos():
    response = client.get(
        "/processos/?page=0",
        headers=auth_headers,
    )
    assert response.status_code == 422

    response = client.get(
        "/processos/?page_size=0",
        headers=auth_headers,
    )
    assert response.status_code == 422

    response = client.get(
        "/processos/?page_size=101",
        headers=auth_headers,
    )
    assert response.status_code == 422
