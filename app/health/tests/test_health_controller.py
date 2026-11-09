from unittest.mock import patch

from app.config import database
from app.health.controller import (
    verificar_banco_conexao,
    verificar_storage_conexao,
)


def test_health_liveness_retorna_200_com_payload_esperado(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "service": "advog-api"}


def test_health_liveness_nao_executa_queries_no_banco(client):
    with patch.object(database.engine, "connect") as mock_connect:
        resposta = client.get("/health")
        assert resposta.status_code == 200
        mock_connect.assert_not_called()


def test_health_readiness_sucesso(client):
    with patch("app.health.controller.verificar_storage_conexao"):
        resposta = client.get("/health/ready")
        assert resposta.status_code == 200
        assert resposta.json() == {
            "status": "ready",
            "database": "ok",
            "storage": "ok",
        }


def test_health_readiness_falha_banco(client):
    with (
        patch("app.health.controller.verificar_banco_conexao", side_effect=Exception("Falha DB")),
        patch("app.health.controller.verificar_storage_conexao"),
    ):
        resposta = client.get("/health/ready")
        assert resposta.status_code == 503
        dados = resposta.json()
        assert dados["status"] == "unhealthy"
        assert "Falha DB" in dados["database"]
        assert dados["storage"] == "ok"


def test_health_readiness_timeout_banco(client):
    with (
        patch("app.health.controller.verificar_banco_conexao", side_effect=TimeoutError),
        patch("app.health.controller.verificar_storage_conexao"),
    ):
        resposta = client.get("/health/ready")
        assert resposta.status_code == 503
        dados = resposta.json()
        assert dados["status"] == "unhealthy"
        assert "timeout" in dados["database"]


def test_health_readiness_falha_storage(client):
    with patch(
        "app.health.controller.verificar_storage_conexao",
        side_effect=Exception("Bucket não encontrado"),
    ):
        resposta = client.get("/health/ready")
        assert resposta.status_code == 503
        dados = resposta.json()
        assert dados["status"] == "unhealthy"
        assert "Bucket não encontrado" in dados["storage"]
        assert dados["database"] == "ok"


def test_health_readiness_timeout_storage(client):
    with patch("app.health.controller.verificar_storage_conexao", side_effect=TimeoutError):
        resposta = client.get("/health/ready")
        assert resposta.status_code == 503
        dados = resposta.json()
        assert dados["status"] == "unhealthy"
        assert "timeout" in dados["storage"]


def test_verificar_banco_conexao_executa_com_sucesso():
    # Deve executar sem erros com a engine de teste conectada
    verificar_banco_conexao()


def test_verificar_storage_conexao_chama_head_bucket():
    with patch("app.health.controller.s3_client.head_bucket") as mock_head:
        verificar_storage_conexao()
        mock_head.assert_called_once()
