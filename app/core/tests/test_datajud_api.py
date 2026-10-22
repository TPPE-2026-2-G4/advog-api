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


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("1000000-00.2026.8.26.0100", "10000000020268260100"),
        ("", ""),
        (None, ""),
    ],
)
def test_sanitizar_cnj(entrada, esperado):
    assert DatajudApiClient.sanitizar_cnj(entrada) == esperado


@pytest.mark.parametrize(
    "cnj,alias_esperado",
    [
        ("10000000020268260100", "tjsp"),
        ("10000000020268270100", "tjto"),
        ("00008323520184013202", "trf1"),
        ("10000000020265020100", "trt2"),
        ("123", None),
        ("10000000020269990100", None),
    ],
)
def test_extrair_alias_tribunal(cnj, alias_esperado):
    assert DatajudApiClient.extrair_alias_tribunal(cnj) == alias_esperado


@pytest.mark.parametrize("cnj_vazio", ["", None])
@pytest.mark.asyncio
async def test_fetch_processo_cnj_vazio(api_client_real, cnj_vazio):
    assert await api_client_real.fetch_processo(cnj_vazio) is None


@pytest.mark.asyncio
async def test_fetch_processo_mock(api_client_mock):
    res = await api_client_mock.fetch_processo("1000000-00.2026.8.26.0100")
    assert res is not None
    assert "status" in res
    assert "data_realizado" in res
    assert res["tribunal"] == "TJSP"


@pytest.mark.asyncio
async def test_fetch_processo_retorna_none_quando_tribunal_desconhecido(api_client_real):
    res = await api_client_real.fetch_processo("10000000020269990100")
    assert res is None


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
    assert res["data_realizado"] is None


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_fetch_processo_data_invalida(mock_post, api_client_real):
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
                                    "nome": "Movimento",
                                    "dataHora": "data_invalida",
                                }
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
    assert res["status"] == "Movimento"
    assert res["data_realizado"] is None


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_fetch_processo_exception(mock_post, api_client_real):
    mock_post.side_effect = Exception("Conexão recusada")

    res = await api_client_real.fetch_processo("1000000-00.2026.8.26.0100")
    assert res is None
