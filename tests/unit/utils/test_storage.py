import io
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from app.config.storage import _obter_variavel_obrigatoria
from app.utils.storage import (
    garantir_bucket,
    obter_url_publica,
    remover_arquivo,
    salvar_arquivo,
)


def test_obter_variavel_obrigatoria_sucesso(monkeypatch):
    monkeypatch.setenv("TEST_VAR", "valor_ok")
    assert _obter_variavel_obrigatoria("TEST_VAR") == "valor_ok"


def test_obter_variavel_obrigatoria_inexistente_lanca_erro(monkeypatch):
    monkeypatch.delenv("TEST_VAR", raising=False)
    with pytest.raises(RuntimeError, match="Variável de ambiente"):
        _obter_variavel_obrigatoria("TEST_VAR")


def test_obter_url_publica_com_chave_none_ou_vazia():
    assert obter_url_publica(None) is None
    assert obter_url_publica("") is None


def test_obter_url_publica_com_chave_valida():
    url = obter_url_publica("logotipos/logo.png")
    assert url is not None
    assert "logotipos/logo.png" in url


@patch("app.utils.storage.s3_client")
def test_garantir_bucket_existente(mock_s3):
    garantir_bucket()
    mock_s3.head_bucket.assert_called_once()


@patch("app.utils.storage.s3_client")
def test_garantir_bucket_inexistente_cria_bucket(mock_s3):
    error_response = {"Error": {"Code": "404"}}
    mock_s3.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    garantir_bucket()

    mock_s3.create_bucket.assert_called_once()


@patch("app.utils.storage.s3_client")
def test_garantir_bucket_erro_diferente_lanca_excecao(mock_s3):
    error_response = {"Error": {"Code": "403"}}
    mock_s3.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    with pytest.raises(ClientError):
        garantir_bucket()


@patch("app.utils.storage.s3_client")
def test_salvar_arquivo_sucesso(mock_s3):
    conteudo = io.BytesIO(b"conteudo teste")
    chave = salvar_arquivo(conteudo, ".png", "image/png", pasta="testes")

    assert chave.startswith("testes/")
    assert chave.endswith(".png")
    mock_s3.upload_fileobj.assert_called_once()


@patch("app.utils.storage.s3_client")
def test_salvar_arquivo_sem_pasta(mock_s3):
    conteudo = io.BytesIO(b"conteudo teste")
    chave = salvar_arquivo(conteudo, "png", "image/png", pasta="")

    assert "/" not in chave
    assert chave.endswith(".png")
    mock_s3.upload_fileobj.assert_called_once()


@patch("app.utils.storage.s3_client")
def test_remover_arquivo_sucesso(mock_s3):
    remover_arquivo("logotipos/antigo.png")
    mock_s3.delete_object.assert_called_once()


def test_remover_arquivo_chave_vazia_nao_chama_s3():
    with patch("app.utils.storage.s3_client") as mock_s3:
        remover_arquivo("")
        remover_arquivo(None)  # type: ignore
        mock_s3.delete_object.assert_not_called()


@patch("app.utils.storage.s3_client")
def test_remover_arquivo_com_erro_client_error_silenciado(mock_s3):
    error_response = {"Error": {"Code": "NoSuchKey"}}
    mock_s3.delete_object.side_effect = ClientError(error_response, "DeleteObject")

    remover_arquivo("logotipos/inexistente.png")
