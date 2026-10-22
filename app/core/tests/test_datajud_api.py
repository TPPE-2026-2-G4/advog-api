import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.datajud_api import DatajudApiClient


@pytest.fixture
def api_client_mock():
    os.environ["DATAJUD_MOCK"] = "true"
    client = DatajudApiClient()
    yield client
    del os.environ["DATAJUD_MOCK"]


@pytest.fixture
def api_client_real():
    if "DATAJUD_MOCK" in os.environ:
        del os.environ["DATAJUD_MOCK"]
    return DatajudApiClient()


def test_sanitizar_cnj():
    assert DatajudApiClient.sanitizar_cnj("1000000-00.2026.8.26.0100") == "10000000020268260100"
    assert DatajudApiClient.sanitizar_cnj("") == ""
    assert DatajudApiClient.sanitizar_cnj(None) == ""


def test_extrair_alias_tribunal():
    # TJSP: 8.26
    assert DatajudApiClient.extrair_alias_tribunal("10000000020268260100") == "tjsp"
    # TRF1: 4.01
    assert DatajudApiClient.extrair_alias_tribunal("00008323520184013202") == "trf1"
    # TRT2: 5.02
    assert DatajudApiClient.extrair_alias_tribunal("10000000020265020100") == "trt2"
    # CNJ inválido ou tamanho errado
    assert DatajudApiClient.extrair_alias_tribunal("123") is None
    # Tribunal desconhecido
    assert DatajudApiClient.extrair_alias_tribunal("10000000020269990100") is None


@pytest.mark.asyncio
async def test_fetch_processo_cnj_vazio(api_client_real):
    assert await api_client_real.fetch_processo("") is None
    assert await api_client_real.fetch_processo(None) is None


@pytest.mark.asyncio
async def test_fetch_processo_mock(api_client_mock):
    res = await api_client_mock.fetch_processo("1000000-00.2026.8.26.0100")
    assert res is not None
    assert "status" in res
    assert "data_realizado" in res
    assert res["tribunal"] == "TJSP"


@pytest.mark.asyncio
async def test_fetch_processo_fallback_mock_quando_tribunal_desconhecido(api_client_real):
    res = await api_client_real.fetch_processo("10000000020269990100")
    assert res is not None
    assert "status" in res
    assert "tribunal" in res


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_fetch_processo_real_sucesso(mock_post, api_client_real):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "tribunal": "TJSP",
                        "dadosBasicos": {
                            "movimento": [
                                {
                                    "codigo": 50,
                                    "nome": "Recebimento",
                                    "dataHora": "2026-02-10T11:30:00Z",
                                },
                                {
                                    "codigo": 11010,
                                    "nome": "Concluso para Despacho",
                                    "dataHora": "2026-02-11T14:20:00Z",
                                },
                            ]
                        },
                    }
                }
            ]
        }
    }
    mock_post.return_value = mock_response

    res = await api_client_real.fetch_processo("1000000-00.2026.8.26.0100")

    assert res is not None
    assert res["status"] == "Concluso para Despacho"
    assert res["tribunal"] == "TJSP"
    assert "data_realizado" in res
    mock_post.assert_called_once()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_fetch_processo_sem_hits(mock_post, api_client_real):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"hits": {"hits": []}}
    mock_post.return_value = mock_response

    res = await api_client_real.fetch_processo("1000000-00.2026.8.26.0100")
    assert res is None


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_fetch_processo_sem_movimentos_usa_status_padrao(mock_post, api_client_real):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "tribunal": "TJSP",
                        "dadosBasicos": {"movimento": []},
                    }
                }
            ]
        }
    }
    mock_post.return_value = mock_response

    res = await api_client_real.fetch_processo("1000000-00.2026.8.26.0100")
    assert res is not None
    assert res["status"] == "Em Andamento"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_fetch_processo_exception(mock_post, api_client_real):
    mock_post.side_effect = Exception("Conexão recusada")

    res = await api_client_real.fetch_processo("1000000-00.2026.8.26.0100")
    assert res is None
