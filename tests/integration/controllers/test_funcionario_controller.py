import pytest

from app.models.funcionario import StatusFuncionario


@pytest.mark.parametrize(
    "nome,email",
    [
        ("Ana Beatriz Souza", "ana.souza@test.com"),
        ("Carlos Eduardo Lima", "carlos.lima@test.com"),
        ("Patrícia Almeida", "patricia.almeida@test.com"),
        ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
        ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
    ],
)
def test_criar_funcionario_retorna_funcionario_criado(client, nome, email):
    response = client.post("/funcionarios", json={"nome": nome, "email": email})
    assert response.status_code == 201
    assert response.json()["nome"] == nome
    assert response.json()["email"] == email.lower()


def test_criar_funcionario_com_email_existente_retorna_erro(client):
    response = client.post(
        "/funcionarios",
        json={"nome": "Funcionario Existente", "email": "funcionario.existente@test.com"},
    )
    assert response.status_code == 201

    response_erro = client.post(
        "/funcionarios",
        json={"nome": "Funcionario Existente 2", "email": "funcionario.existente@test.com"},
    )

    assert response_erro.status_code == 400
    assert response_erro.json()["detail"] == "Email já cadastrado"


def test_buscar_todos_funcionarios_com_funcionarios_cadastrados_retorna_lista(client):
    response = client.post(
        "/funcionarios", json={"nome": "Funcionario 1", "email": "funcionario.1@test.com"}
    )
    assert response.status_code == 201
    response = client.post(
        "/funcionarios", json={"nome": "Funcionario 2", "email": "funcionario.2@test.com"}
    )
    assert response.status_code == 201

    response = client.get("/funcionarios")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["nome"] == "Funcionario 1"
    assert response.json()[0]["email"] == "funcionario.1@test.com"
    assert response.json()[1]["nome"] == "Funcionario 2"
    assert response.json()[1]["email"] == "funcionario.2@test.com"
    assert isinstance(response.json(), list)


def test_buscar_todos_funcionarios_sem_funcionarios_cadastrados_retorna_lista_vazia(client):
    response = client.get("/funcionarios")
    assert response.status_code == 200
    assert response.json() == []
    assert isinstance(response.json(), list)


@pytest.mark.parametrize(
    "nome,email",
    [
        ("Ana Beatriz Souza", "ana.souza@test.com"),
        ("Carlos Eduardo Lima", "carlos.lima@test.com"),
        ("Patrícia Almeida", "patricia.almeida@test.com"),
        ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
        ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
    ],
)
def test_primeiro_acesso_retorna_funcionario_atualizado(client, nome, email):
    response = client.post("/funcionarios", json={"nome": nome, "email": email})
    assert response.status_code == 201
    assert response.json()["nome"] == nome
    assert response.json()["email"] == email.lower()
    assert response.json()["status"] == StatusFuncionario.PENDENTE.value

    funcionario_id = response.json()["funcionario_id"]
    response = client.patch(
        f"/funcionarios/{funcionario_id}/primeiro-acesso", json={"senha": "senha123"}
    )
    assert response.status_code == 200
    assert response.json()["nome"] == nome
    assert response.json()["email"] == email.lower()
    assert response.json()["status"] == StatusFuncionario.ATIVO.value


def test_primeiro_acesso_funcionario_nao_encontrado_retorna_erro(client):
    response = client.patch("/funcionarios/999/primeiro-acesso", json={"senha": "senha123"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Funcionário não encontrado"


def test_primeiro_acesso_funcionario_ja_ativado_retorna_erro(client):
    response = client.post(
        "/funcionarios", json={"nome": "Funcionario Ativo", "email": "funcionario.ativo@test.com"}
    )
    assert response.status_code == 201

    funcionario_id = response.json()["funcionario_id"]
    response = client.patch(
        f"/funcionarios/{funcionario_id}/primeiro-acesso", json={"senha": "senha123"}
    )
    assert response.status_code == 200

    response = client.patch(
        f"/funcionarios/{funcionario_id}/primeiro-acesso", json={"senha": "senha456"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Funcionário já teve a conta ativada"


@pytest.mark.parametrize(
    "nome,email",
    [
        ("Ana Beatriz Souza", "ana.souza@test.com"),
        ("Carlos Eduardo Lima", "carlos.lima@test.com"),
        ("Patrícia Almeida", "patricia.almeida@test.com"),
        ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
        ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
    ],
)
def test_mudar_acesso_funcionario_muda_atividade_e_manda_funcionario_atualizado(
    client, nome, email
):
    response = client.post("/funcionarios", json={"nome": nome, "email": email})
    assert response.status_code == 201

    funcionario_id = response.json()["funcionario_id"]
    response = client.patch(
        f"/funcionarios/{funcionario_id}/primeiro-acesso", json={"senha": "senha123"}
    )
    assert response.status_code == 200

    response = client.patch(f"/funcionarios/{funcionario_id}/mudar-acesso")
    assert response.status_code == 200
    assert response.json()["nome"] == nome
    assert response.json()["email"] == email.lower()
    assert response.json()["status"] == StatusFuncionario.INATIVO.value

    response = client.patch(f"/funcionarios/{funcionario_id}/mudar-acesso")
    assert response.status_code == 200
    assert response.json()["nome"] == nome
    assert response.json()["email"] == email.lower()
    assert response.json()["status"] == StatusFuncionario.ATIVO.value


def test_mudar_acesso_funcionario_nao_encontrado_retorna_erro(client):
    response = client.patch("/funcionarios/999/mudar-acesso")
    assert response.status_code == 400
    assert response.json()["detail"] == "Funcionário não encontrado"


def test_mudar_acesso_funcionario_com_conta_pendente_retorna_erro(client):
    response = client.post(
        "/funcionarios",
        json={"nome": "Funcionario Pendente", "email": "funcionario.pendente@test.com"},
    )
    assert response.status_code == 201

    funcionario_id = response.json()["funcionario_id"]
    response = client.patch(f"/funcionarios/{funcionario_id}/mudar-acesso")
    assert response.status_code == 400
    assert response.json()["detail"] == "Funcionário ainda não ativou a conta"


@pytest.mark.parametrize(
    "nome,email",
    [
        ("Ana Beatriz Souza", "ana.souza@test.com"),
        ("Carlos Eduardo Lima", "carlos.lima@test.com"),
        ("Patrícia Almeida", "patricia.almeida@test.com"),
        ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
        ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
    ],
)
def test_apagar_funcionario_retorna_funcionario_apagado(client, nome, email):
    response = client.post("/funcionarios", json={"nome": nome, "email": email})
    assert response.status_code == 201

    funcionario_id = response.json()["funcionario_id"]
    response = client.delete(f"/funcionarios/{funcionario_id}")
    assert response.status_code == 200
    assert response.json()["nome"] == nome
    assert response.json()["email"] == email.lower()


def test_apagar_funcionario_nao_encontrado_retorna_erro(client):
    response = client.delete("/funcionarios/999")
    assert response.status_code == 400
    assert response.json()["detail"] == "Funcionário não encontrado"
