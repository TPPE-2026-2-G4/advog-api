from unittest.mock import MagicMock

import pytest

from app.models.funcionario import Funcionario, StatusFuncionario
from app.repositories.funcionario import FuncionarioRepository
from app.schemas.auth import LoginRequest
from app.services.auth import AuthService, ContaNaoAtivaError, CredenciaisInvalidasError
from app.utils.seguranca import hash_senha


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
