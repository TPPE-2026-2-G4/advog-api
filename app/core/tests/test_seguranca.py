import importlib
from unittest.mock import patch

import jwt
import pytest

from app.core import seguranca
from app.core.seguranca import (
    DEV_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_SECRET,
    criar_token_primeiro_acesso,
    criar_token_recuperacao,
    extrair_funcionario_id_do_token,
    hash_senha,
    hash_token_recuperacao,
    validar_secret_key,
    validar_token_primeiro_acesso,
    verificar_senha,
)


def test_hash_senha_gera_hash_diferente_da_senha_original():
    senha = "pytest123"
    senha_hash = hash_senha(senha)

    assert senha != senha_hash
    assert senha_hash.startswith("$2b$")


def test_hash_senha_gera_hash_diferente_para_senhas_iguais():
    senha = "pytest123"

    assert hash_senha(senha) != hash_senha(senha)


def test_verificar_senha_retorna_true_para_senha_correta():
    senha = "pytest123"
    senha_hash = hash_senha(senha)

    assert verificar_senha(senha, senha_hash) is True


def test_verificar_senha_retorna_false_para_senha_incorreta():
    senha = "pytest123"
    senha_hash = hash_senha(senha)

    assert verificar_senha("senha_incorreta", senha_hash) is False


def test_criar_token_recuperacao_retorna_token_e_hash_verificavel():
    token, token_hash = criar_token_recuperacao()

    assert token
    assert token_hash == hash_token_recuperacao(token)
    assert token_hash != token


def test_validar_token_primeiro_acesso_sucesso():
    token = criar_token_primeiro_acesso(123)
    funcionario_id = validar_token_primeiro_acesso(token)

    assert funcionario_id == 123


def test_validar_token_primeiro_acesso_token_invalido_lanca_erro():
    with pytest.raises(ValueError, match="inválido"):
        validar_token_primeiro_acesso("token_invalido_malformado")


def test_validar_token_primeiro_acesso_tipo_diferente_lanca_erro():
    token = jwt.encode(
        {"funcionario_id": 123, "tipo": "acesso_normal"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(ValueError, match="inválido"):
        validar_token_primeiro_acesso(token)


def test_validar_token_primeiro_acesso_erro_decodificacao_lanca_erro():
    with (
        patch("app.core.seguranca.decodificar_token", side_effect=jwt.PyJWTError),
        pytest.raises(ValueError, match="inválido"),
    ):
        validar_token_primeiro_acesso("token_jwt_qualquer")


def test_extrair_funcionario_id_do_token_sucesso():
    token = jwt.encode({"sub": "123"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert extrair_funcionario_id_do_token(token) == 123


def test_extrair_funcionario_id_do_token_token_invalido_lanca_erro():
    with pytest.raises(ValueError, match="Token inválido ou expirado"):
        extrair_funcionario_id_do_token("token_invalido")


def test_extrair_funcionario_id_do_token_sem_sub_lanca_erro():
    token = jwt.encode({"outro_campo": "valor"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    with pytest.raises(ValueError, match="Token inválido"):
        extrair_funcionario_id_do_token(token)


def test_validar_secret_key_producao_ausente_lanca_erro():
    with pytest.raises(RuntimeError, match="SECRET_KEY é obrigatória em ambiente de produção"):
        validar_secret_key(None, "production")

    with pytest.raises(RuntimeError, match="SECRET_KEY é obrigatória em ambiente de produção"):
        validar_secret_key("   ", "production")


def test_validar_secret_key_producao_valor_desenvolvimento_lanca_erro():
    with pytest.raises(
        RuntimeError,
        match="SECRET_KEY não pode ser o valor padrão de desenvolvimento em ambiente de produção",
    ):
        validar_secret_key(DEV_SECRET_KEY, "production")

    with pytest.raises(
        RuntimeError,
        match="SECRET_KEY não pode ser o valor padrão de desenvolvimento em ambiente de produção",
    ):
        validar_secret_key("dev", "production")


def test_validar_secret_key_producao_curta_lanca_erro():
    with pytest.raises(RuntimeError, match="deve ter pelo menos 32 caracteres"):
        validar_secret_key("a" * 31, "production")

    assert validar_secret_key("a" * 32, "production") == "a" * 32


def test_validar_secret_key_producao_valida_sucesso():
    chave_segura = "minha-chave-producao-super-segura-e-longa-32"
    assert validar_secret_key(chave_segura, "production") == chave_segura


def test_validar_secret_key_desenvolvimento_fallback():
    assert validar_secret_key(None, "development") == DEV_SECRET_KEY
    assert validar_secret_key("", "development") == DEV_SECRET_KEY


def test_validar_secret_key_desenvolvimento_customizada():
    assert validar_secret_key("chave-dev", "development") == "chave-dev"


def test_startup_aborta_se_secret_key_ausente_em_producao(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY é obrigatória"):
        importlib.reload(seguranca)

    # Restaura módulo com ambiente de teste
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("JWT_SECRET", "super_secret_jwt_key")
    importlib.reload(seguranca)
