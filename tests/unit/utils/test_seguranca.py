from unittest.mock import patch

import jwt
import pytest

from app.utils.seguranca import (
    JWT_ALGORITHM,
    JWT_SECRET,
    criar_token_primeiro_acesso,
    extrair_funcionario_id_do_token,
    hash_senha,
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
        patch("app.utils.seguranca.decodificar_token", side_effect=jwt.PyJWTError),
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
