import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.cargo import Cargo
from app.models.funcionario import Funcionario, StatusFuncionario


@pytest.fixture
def cargo_db(db_session: Session) -> Cargo:
    cargo = Cargo()
    cargo.nome_cargo = "Advogado Pleno"
    cargo.descricao = "Descrição inicial"
    cargo.permissao = {
        "visualizar_processos": True,
        "criar_processos": False,
        "editar_processos": False,
        "excluir_processos": False,
        "visualizar_financeiro": False,
        "gerenciar_financeiro": False,
        "visualizar_equipe": False,
        "gerenciar_equipe": False,
        "configuracoes_sistema": False,
    }
    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)
    return cargo


@pytest.fixture
def cargo_com_funcionario_db(db_session: Session) -> Cargo:
    cargo = Cargo()
    cargo.nome_cargo = "Gerente Jurídico"
    cargo.descricao = "Gestão de equipe"
    cargo.permissao = {}
    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)

    funcionario = Funcionario(
        nome="Carlos Silva",
        email="carlos@empresa.com",
        cargo_id=cargo.cargo_id,
        status=StatusFuncionario.ATIVO,
    )
    db_session.add(funcionario)
    db_session.commit()

    return cargo


def test_buscar_todos_cargos_retorna_lista(client: TestClient, cargo_db: Cargo):
    response = client.get("/cargos")

    assert response.status_code == 200
    dados = response.json()
    assert isinstance(dados, list)
    assert len(dados) >= 1
    assert dados[0]["nome_cargo"] == "Advogado Pleno"


def test_criar_cargo_sucesso(client: TestClient):
    payload = {"nome_cargo": "Analista de Compliance", "descricao": "Auditoria"}

    response = client.post("/cargos", json=payload)

    assert response.status_code == 201
    dados = response.json()
    assert dados["cargo_id"] is not None
    assert dados["nome_cargo"] == "Analista de Compliance"


def test_criar_cargo_nome_duplicado_retorna_400(client: TestClient, cargo_db: Cargo):
    payload = {"nome_cargo": "Advogado Pleno"}

    response = client.post("/cargos", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Cargo já cadastrado"


def test_buscar_cargo_por_id_sucesso(client: TestClient, cargo_db: Cargo):
    response = client.get(f"/cargos/{cargo_db.cargo_id}")

    assert response.status_code == 200
    dados = response.json()
    assert dados["cargo_id"] == cargo_db.cargo_id
    assert dados["nome_cargo"] == "Advogado Pleno"
    assert dados["permissao"]["visualizar_processos"] is True


def test_buscar_cargo_por_id_inexistente_retorna_404(client: TestClient):
    response = client.get("/cargos/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cargo não encontrado"


def test_atualizar_cargo_sucesso(client: TestClient, cargo_db: Cargo):
    payload = {
        "nome_cargo": "Advogado Senior",
        "descricao": "Descrição atualizada",
        "permissao": {
            "visualizar_processos": True,
            "criar_processos": True,
            "editar_processos": True,
            "excluir_processos": False,
            "visualizar_financeiro": True,
            "gerenciar_financeiro": False,
            "visualizar_equipe": True,
            "gerenciar_equipe": False,
            "configuracoes_sistema": False,
        },
    }

    response = client.put(f"/cargos/{cargo_db.cargo_id}", json=payload)

    assert response.status_code == 200
    dados = response.json()
    assert dados["nome_cargo"] == "Advogado Senior"
    assert dados["descricao"] == "Descrição atualizada"
    assert dados["permissao"]["criar_processos"] is True
    assert dados["permissao"]["visualizar_financeiro"] is True


def test_atualizar_cargo_nome_duplicado_retorna_400(
    client: TestClient, cargo_db: Cargo, db_session
):
    client.post("/cargos", json={"nome_cargo": "Sócio"})

    payload = {"nome_cargo": "Sócio"}

    response = client.put(f"/cargos/{cargo_db.cargo_id}", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Cargo já cadastrado"


def test_atualizar_cargo_inexistente_retorna_404(client: TestClient):
    payload = {"nome_cargo": "Cargo Fantasma"}

    response = client.put("/cargos/99999", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Cargo não encontrado"


def test_deletar_cargo_sem_funcionarios_sucesso(client: TestClient, cargo_db: Cargo):
    response = client.delete(f"/cargos/{cargo_db.cargo_id}")

    assert response.status_code == 200
    assert response.json()["cargo_id"] == cargo_db.cargo_id

    response_busca = client.get(f"/cargos/{cargo_db.cargo_id}")
    assert response_busca.status_code == 404


def test_deletar_cargo_com_funcionarios_vinculados_retorna_400(
    client: TestClient, cargo_com_funcionario_db: Cargo
):
    response = client.delete(f"/cargos/{cargo_com_funcionario_db.cargo_id}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Não é possível excluir um cargo associado a funcionários"


def test_deletar_cargo_inexistente_retorna_404(client: TestClient):
    response = client.delete("/cargos/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cargo não encontrado"
