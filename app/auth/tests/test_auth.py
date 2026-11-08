from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.model import TokenRecuperacaoSenha
from app.auth.schema import LoginRequest
from app.auth.service import AuthService, ContaNaoAtivaError, CredenciaisInvalidasError
from app.config.limiter import limiter
from app.core.seguranca import hash_senha, hash_token_recuperacao
from app.funcionario.model import Funcionario, StatusFuncionario
from app.funcionario.repository import FuncionarioRepository


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()


class TestLoginController:
    @pytest.mark.parametrize(
        "nome,email,senha",
        [
            ("Ana Beatriz Souza", "ana.souza@test.com", "senhaForte123"),
            ("Carlos Eduardo Lima", "carlos.lima@test.com", "outraSenha456"),
            ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM", "senhaComLetrasEMais"),
        ],
    )
    def test_login_com_sucesso_retorna_token_e_dados(
        self,
        client,
        cargo_padrao,
        atuacao_padrao,
        token_primeiro_acesso,
        token_admin,
        nome,
        email,
        senha,
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        criacao = client.post(
            "/funcionarios",
            json={
                "nome": nome,
                "email": email,
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert criacao.status_code == 201
        funcionario_id = criacao.json()["funcionario_id"]

        ativacao = client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": senha, "token": token_primeiro_acesso(funcionario_id)},
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

    def test_login_email_nao_cadastrado_retorna_401(self, client):
        response = client.post(
            "/auth/login", json={"email": "naoexiste@test.com", "senha": "qualquer_senha"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Email ou senha incorretos"

    def test_login_senha_incorreta_retorna_401(
        self, client, cargo_padrao, atuacao_padrao, token_primeiro_acesso, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        criacao = client.post(
            "/funcionarios",
            json={
                "nome": "Advogado Teste",
                "email": "advogado@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        funcionario_id = criacao.json()["funcionario_id"]
        client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": "senhaCorreta123", "token": token_primeiro_acesso(funcionario_id)},
        )

        response = client.post(
            "/auth/login", json={"email": "advogado@test.com", "senha": "senhaIncorreta123"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Email ou senha incorretos"

    def test_login_usuario_pendente_retorna_401(
        self, client, cargo_padrao, atuacao_padrao, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        client.post(
            "/funcionarios",
            json={
                "nome": "Pendente Teste",
                "email": "pendente@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )

        response = client.post(
            "/auth/login", json={"email": "pendente@test.com", "senha": "qualquer_senha"}
        )
        assert response.status_code == 401

    def test_login_usuario_com_senha_mas_pendente_retorna_403(
        self, client, db_session, cargo_padrao, atuacao_padrao
    ):
        func = Funcionario(
            atuacao_id=1,
            foto_perfil=1,
            nome="Pendente Com Senha",
            email="pendente.senha@test.com",
            senha_hash=hash_senha("senha123"),
            status=StatusFuncionario.PENDENTE,
            cargo_id=cargo_padrao.cargo_id,
        )
        db_session.add(func)
        db_session.commit()

        response = client.post(
            "/auth/login", json={"email": "pendente.senha@test.com", "senha": "senha123"}
        )
        assert response.status_code == 403
        assert "primeiro acesso" in response.json()["detail"]

    def test_login_usuario_inativo_retorna_403(
        self, client, cargo_padrao, atuacao_padrao, token_primeiro_acesso, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        criacao = client.post(
            "/funcionarios",
            json={
                "nome": "Inativo Teste",
                "email": "inativo@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        funcionario_id = criacao.json()["funcionario_id"]
        client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": "senhaCorreta123", "token": token_primeiro_acesso(funcionario_id)},
        )
        client.patch(f"/funcionarios/{funcionario_id}/mudar-acesso", headers=headers)

        response = client.post(
            "/auth/login", json={"email": "inativo@test.com", "senha": "senhaCorreta123"}
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Conta inativa. Entre em contato com o administrador."


class TestLoginValidacoesERateLimit:
    def test_login_email_invalido_retorna_422(self, client):
        response = client.post("/auth/login", json={"email": "email_invalido", "senha": "senha123"})
        assert response.status_code == 422

    def test_login_senha_em_branco_retorna_422(self, client):
        response = client.post("/auth/login", json={"email": "valido@test.com", "senha": ""})
        assert response.status_code == 422

    def test_login_rate_limiting_retorna_429(self, client):
        respostas = [
            client.post(
                "/auth/login",
                json={"email": "rate@test.com", "senha": "qualquer_senha"},
            ).status_code
            for _ in range(15)
        ]
        assert 429 in respostas


def test_init_auth_service():
    mock_session = MagicMock()
    service = AuthService(mock_session)
    assert isinstance(service.repository, FuncionarioRepository)
    assert service.repository.db == mock_session


def test_autenticar_com_sucesso():
    service = AuthService.__new__(AuthService)
    service.repository = MagicMock(spec=FuncionarioRepository)

    senha_plana = "senhaSegura123"
    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        funcionario_id=1,
        nome="Advogado Teste",
        email="advogado@test.com",
        senha_hash=hash_senha(senha_plana),
        status=StatusFuncionario.ATIVO,
    )
    service.repository.buscar_por_email.return_value = funcionario

    dados = LoginRequest(email="Advogado@Test.com", senha=senha_plana)
    token, usuario = service.autenticar(dados)

    assert isinstance(token, str)
    assert usuario.funcionario_id == 1
    assert usuario.email == "advogado@test.com"
    service.repository.buscar_por_email.assert_called_once_with("advogado@test.com")


def test_autenticar_email_inexistente_lanca_erro():
    service = AuthService.__new__(AuthService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_email.return_value = None

    dados = LoginRequest(email="inexistente@test.com", senha="qualquer_senha")
    with pytest.raises(CredenciaisInvalidasError, match="Email ou senha incorretos"):
        service.autenticar(dados)


def test_autenticar_funcionario_sem_senha_hash_lanca_erro():
    service = AuthService.__new__(AuthService)
    service.repository = MagicMock(spec=FuncionarioRepository)

    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        funcionario_id=1,
        nome="Pendente Teste",
        email="pendente@test.com",
        senha_hash=None,
        status=StatusFuncionario.PENDENTE,
    )
    service.repository.buscar_por_email.return_value = funcionario

    dados = LoginRequest(email="pendente@test.com", senha="qualquer_senha")
    with pytest.raises(CredenciaisInvalidasError, match="Email ou senha incorretos"):
        service.autenticar(dados)


def test_autenticar_senha_incorreta_lanca_erro():
    service = AuthService.__new__(AuthService)
    service.repository = MagicMock(spec=FuncionarioRepository)

    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        funcionario_id=1,
        nome="Advogado Teste",
        email="advogado@test.com",
        senha_hash=hash_senha("senhaCorreta123"),
        status=StatusFuncionario.ATIVO,
    )
    service.repository.buscar_por_email.return_value = funcionario

    dados = LoginRequest(email="advogado@test.com", senha="senhaErrada123")
    with pytest.raises(CredenciaisInvalidasError, match="Email ou senha incorretos"):
        service.autenticar(dados)


def test_autenticar_funcionario_status_pendente_lanca_erro():
    service = AuthService.__new__(AuthService)
    service.repository = MagicMock(spec=FuncionarioRepository)

    senha_plana = "senha123"
    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        funcionario_id=1,
        nome="Funcionario Pendente",
        email="pendente@test.com",
        senha_hash=hash_senha(senha_plana),
        status=StatusFuncionario.PENDENTE,
    )
    service.repository.buscar_por_email.return_value = funcionario

    dados = LoginRequest(email="pendente@test.com", senha=senha_plana)
    with pytest.raises(ContaNaoAtivaError, match="Conta pendente de ativação"):
        service.autenticar(dados)


def test_autenticar_funcionario_status_inativo_lanca_erro():
    service = AuthService.__new__(AuthService)
    service.repository = MagicMock(spec=FuncionarioRepository)

    senha_plana = "senha123"
    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        funcionario_id=1,
        nome="Funcionario Inativo",
        email="inativo@test.com",
        senha_hash=hash_senha(senha_plana),
        status=StatusFuncionario.INATIVO,
    )
    service.repository.buscar_por_email.return_value = funcionario

    dados = LoginRequest(email="inativo@test.com", senha=senha_plana)
    with pytest.raises(ContaNaoAtivaError, match="Conta inativa"):
        service.autenticar(dados)


class TestRecuperacaoSenhaController:
    mensagem_padrao = (
        "Se o e-mail estiver cadastrado, você receberá um link para redefinir sua senha."
    )

    def test_solicitar_recuperacao_cria_token_e_envia_email(
        self, client, db_session, funcionario_admin, monkeypatch
    ):
        enviar_email = AsyncMock()
        monkeypatch.setattr("app.auth.controller.enviar_email_recuperacao_senha", enviar_email)

        response = client.post(
            "/auth/esqueci-senha", json={"email": funcionario_admin.email.upper()}
        )

        assert response.status_code == 200
        assert response.json() == {"mensagem": self.mensagem_padrao}
        enviar_email.assert_awaited_once()
        token = enviar_email.await_args.args[2]
        token_salvo = db_session.query(TokenRecuperacaoSenha).one()
        assert token_salvo.token_hash == hash_token_recuperacao(token)
        assert token_salvo.token_hash != token
        assert token_salvo.usado_em is None

    @pytest.mark.parametrize("email", ["inexistente@test.com", "admin.fixture@test.com"])
    def test_solicitar_recuperacao_nao_revela_se_email_existe(
        self, client, email, funcionario_admin, monkeypatch
    ):
        enviar_email = AsyncMock()
        monkeypatch.setattr("app.auth.controller.enviar_email_recuperacao_senha", enviar_email)

        response = client.post("/auth/esqueci-senha", json={"email": email})

        assert response.status_code == 200
        assert response.json() == {"mensagem": self.mensagem_padrao}
        if email == funcionario_admin.email:
            enviar_email.assert_awaited_once()
        else:
            enviar_email.assert_not_awaited()

    def test_solicitar_recuperacao_retorna_422_para_email_invalido(self, client):
        response = client.post("/auth/esqueci-senha", json={"email": "email-invalido"})

        assert response.status_code == 422

    def test_solicitar_recuperacao_nao_envia_email_para_conta_inativa(
        self, client, db_session, cargo_padrao, monkeypatch
    ):
        funcionario = Funcionario(
            atuacao_id=1,
            foto_perfil=1,
            nome="Conta Inativa",
            email="conta.inativa@test.com",
            senha_hash=hash_senha("senha123"),
            status=StatusFuncionario.INATIVO,
            cargo_id=cargo_padrao.cargo_id,
        )
        db_session.add(funcionario)
        db_session.commit()
        enviar_email = AsyncMock()
        monkeypatch.setattr("app.auth.controller.enviar_email_recuperacao_senha", enviar_email)

        response = client.post("/auth/esqueci-senha", json={"email": "conta.inativa@test.com"})

        assert response.status_code == 200
        enviar_email.assert_not_awaited()

    def test_solicitar_recuperacao_aplica_rate_limit(self, client):
        respostas = [
            client.post("/auth/esqueci-senha", json={"email": "inexistente@test.com"}).status_code
            for _ in range(6)
        ]

        assert 429 in respostas

    def test_redefinir_senha_atualiza_senha_e_invalida_token(
        self, client, funcionario_admin, monkeypatch
    ):
        enviar_email = AsyncMock()
        monkeypatch.setattr("app.auth.controller.enviar_email_recuperacao_senha", enviar_email)
        client.post("/auth/esqueci-senha", json={"email": funcionario_admin.email})
        token = enviar_email.await_args.args[2]

        response = client.post(
            "/auth/redefinir-senha", json={"token": token, "senha": "novaSenha123"}
        )

        assert response.status_code == 200
        assert response.json() == {"mensagem": "Senha redefinida com sucesso."}
        login = client.post(
            "/auth/login", json={"email": funcionario_admin.email, "senha": "novaSenha123"}
        )
        assert login.status_code == 200

        reutilizacao = client.post(
            "/auth/redefinir-senha", json={"token": token, "senha": "outraSenha123"}
        )
        assert reutilizacao.status_code == 400
        assert reutilizacao.json()["detail"] == "Token inválido ou expirado"

    def test_nova_solicitacao_invalida_token_anterior(
        self, client, db_session, funcionario_admin, monkeypatch
    ):
        enviar_email = AsyncMock()
        monkeypatch.setattr("app.auth.controller.enviar_email_recuperacao_senha", enviar_email)

        client.post("/auth/esqueci-senha", json={"email": funcionario_admin.email})
        primeiro_token = enviar_email.await_args.args[2]
        client.post("/auth/esqueci-senha", json={"email": funcionario_admin.email})
        segundo_token = enviar_email.await_args.args[2]

        tokens = (
            db_session.query(TokenRecuperacaoSenha).order_by(TokenRecuperacaoSenha.token_id).all()
        )
        assert len(tokens) == 2
        assert tokens[0].usado_em is not None
        assert tokens[1].usado_em is None

        resposta_primeiro = client.post(
            "/auth/redefinir-senha", json={"token": primeiro_token, "senha": "novaSenha123"}
        )
        resposta_segundo = client.post(
            "/auth/redefinir-senha", json={"token": segundo_token, "senha": "novaSenha123"}
        )
        assert resposta_primeiro.status_code == 400
        assert resposta_segundo.status_code == 200

    @pytest.mark.parametrize(
        "payload",
        [
            {"token": "token-invalido", "senha": "novaSenha123"},
            {"token": "token-valido", "senha": "curta"},
        ],
    )
    def test_redefinir_senha_rejeita_payload_invalido(self, client, payload):
        response = client.post("/auth/redefinir-senha", json=payload)

        assert response.status_code in (400, 422)

    def test_redefinir_senha_rejeita_token_expirado(self, client, db_session, funcionario_admin):
        from datetime import UTC, datetime, timedelta

        db_session.add(
            TokenRecuperacaoSenha(
                funcionario_id=funcionario_admin.funcionario_id,
                token_hash=hash_token_recuperacao("token-expirado"),
                criado_em=datetime.now(UTC) - timedelta(hours=1),
                expira_em=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        db_session.commit()

        response = client.post(
            "/auth/redefinir-senha",
            json={"token": "token-expirado", "senha": "novaSenha123"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Token inválido ou expirado"
