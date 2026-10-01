import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.utils.jusbrasil_api import JusbrasilApiClient
import os


@pytest.fixture
def api_client_mock():
    if "JUSBRASIL_API_TOKEN" in os.environ:
        del os.environ["JUSBRASIL_API_TOKEN"]
    return JusbrasilApiClient()


@pytest.fixture
def api_client_real():
    os.environ["JUSBRASIL_API_TOKEN"] = "token_falso"
    client = JusbrasilApiClient()
    return client


@pytest.mark.asyncio
async def test_fetch_processo_mock(api_client_mock):
    res = await api_client_mock.fetch_processo("123")
    assert res is not None
    assert "status" in res
    assert "data_realizado" in res


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_processo_real_sucesso(mock_get, api_client_real):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"situacao": "Concluído", "tribunal": {"sigla": "TJSP"}}
    mock_get.return_value = mock_response

    res = await api_client_real.fetch_processo("123")

    assert res is not None
    assert res["status"] == "Concluído"
    assert res["tribunal"] == "TJSP"
    mock_get.assert_called_once()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_processo_real_exception(mock_get, api_client_real):
    mock_get.side_effect = Exception("Conexão recusada")

    res = await api_client_real.fetch_processo("123")
    assert res is None
