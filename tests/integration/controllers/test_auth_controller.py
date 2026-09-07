import pytest

from app.config.limiter import limiter
from app.models.funcionario import StatusFuncionario


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest.mark.parametrize(
    "nome,email,senha",
    [
        ("Ana Beatriz Souza", "ana.souza@test.com", "senhaForte123"),
        ("Carlos Eduardo Lima", "carlos.lima@test.com", "outraSenha456"),
        ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM", "senhaComLetrasEMais"),
    ],
)
def test_login_com_sucesso_retorna_token_e_dados(client, nome, email, senha):
    criacao = client.post("/funcionarios", json={"nome": nome, "email": email})
    assert criacao.status_code == 201
    funcionario_id = criacao.json()["funcionario_id"]

    ativacao = client.patch(
        f"/funcionarios/{funcionario_id}/primeiro-acesso", json={"senha": senha}
    )
    assert ativacao.status_code == 200

    response = client.post("/auth/login", json={"email": email, "senha": senha})
    assert response.status_code == 200
    dados = response.json()
    assert "access_token" in dados
    assert dados["token_type"] == "bearer"
    assert dados["funcionario"]["funcionario_id"] == funcionario_id
    assert dados["funcionario"]["email"] == email.lower()
    assert dados["funcionario"]["status"] == StatusFuncionario.ATIVO.value


def test_login_email_nao_cadastrado_retorna_401(client):
    response = client.post(
        "/auth/login", json={"email": "naoexiste@test.com", "senha": "qualquer_senha"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha incorretos"


def test_login_senha_incorreta_retorna_401(client):
    criacao = client.post(
        "/funcionarios", json={"nome": "Advogado Teste", "email": "advogado@test.com"}
    )
    funcionario_id = criacao.json()["funcionario_id"]
    client.patch(
        f"/funcionarios/{funcionario_id}/primeiro-acesso", json={"senha": "senhaCorreta123"}
    )

    response = client.post(
        "/auth/login", json={"email": "advogado@test.com", "senha": "senhaIncorreta123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha incorretos"


def test_login_usuario_pendente_retorna_403(client):
    client.post("/funcionarios", json={"nome": "Pendente Teste", "email": "pendente@test.com"})

    response = client.post(
        "/auth/login", json={"email": "pendente@test.com", "senha": "qualquer_senha"}
    )
    assert response.status_code == 401


def test_login_usuario_com_senha_mas_pendente_retorna_403(client, db_session):
    from app.models.funcionario import Funcionario
    from app.utils.seguranca import hash_senha

    func = Funcionario(
        nome="Pendente Com Senha",
        email="pendente.senha@test.com",
        senha_hash=hash_senha("senha123"),
        status=StatusFuncionario.PENDENTE,
    )
    db_session.add(func)
    db_session.commit()

    response = client.post(
        "/auth/login", json={"email": "pendente.senha@test.com", "senha": "senha123"}
    )
    assert response.status_code == 403
    assert "primeiro acesso" in response.json()["detail"]


def test_login_usuario_inativo_retorna_403(client):
    criacao = client.post(
        "/funcionarios", json={"nome": "Inativo Teste", "email": "inativo@test.com"}
    )
    funcionario_id = criacao.json()["funcionario_id"]
    client.patch(
        f"/funcionarios/{funcionario_id}/primeiro-acesso", json={"senha": "senhaCorreta123"}
    )
    client.patch(f"/funcionarios/{funcionario_id}/mudar-acesso")

    response = client.post(
        "/auth/login", json={"email": "inativo@test.com", "senha": "senhaCorreta123"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Conta inativa. Entre em contato com o administrador."


def test_login_email_invalido_retorna_422(client):
    response = client.post("/auth/login", json={"email": "email_invalido", "senha": "senha123"})
    assert response.status_code == 422


def test_login_senha_em_branco_retorna_422(client):
    response = client.post("/auth/login", json={"email": "valido@test.com", "senha": ""})
    assert response.status_code == 422


def test_login_rate_limiting_retorna_429(client):
    respostas = []
    for _ in range(15):
        resp = client.post(
            "/auth/login", json={"email": "rate@test.com", "senha": "qualquer_senha"}
        )
        respostas.append(resp.status_code)

    assert 429 in respostas
