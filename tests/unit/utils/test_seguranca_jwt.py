import jwt
import pytest

from app.utils.seguranca import criar_token_acesso, decodificar_token


def test_criar_e_decodificar_token_com_sucesso():
    dados = {"sub": "1", "email": "advogado@test.com"}
    token = criar_token_acesso(dados, tempo_expiracao_minutos=30)

    assert isinstance(token, str)

    payload = decodificar_token(token)
    assert payload["sub"] == "1"
    assert payload["email"] == "advogado@test.com"
    assert "exp" in payload
    assert "iat" in payload


def test_decodificar_token_invalido_lanca_erro():
    with pytest.raises(jwt.InvalidTokenError):
        decodificar_token("token_totalmente_invalido.123.abc")


def test_decodificar_token_expirado_lanca_erro():
    dados = {"sub": "1", "email": "advogado@test.com"}
    token = criar_token_acesso(dados, tempo_expiracao_minutos=-10)

    with pytest.raises(jwt.ExpiredSignatureError):
        decodificar_token(token)
