import pytest
from fastapi.testclient import TestClient


def test_registrar_solicitacao_endpoint_sucesso(client: TestClient):
    payload = {
        "nome": "Fernanda Lima",
        "email": "fernanda@email.com",
        "telefone": "(61) 98888-5555",
        "descricao": "Gostaria de agendar uma consulta presencial para tratar de causa trabalhista.",
    }

    resposta = client.post("/solicitacoes", json=payload)

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["nome"] == "Fernanda Lima"
    assert dados["email"] == "fernanda@email.com"
    assert dados["telefone"] == "61988885555"
    assert "id" in dados


@pytest.mark.parametrize(
    "payload_corrompido",
    [
        {
            "nome": "Ab",
            "email": "ana@email.com",
            "telefone": "61999998888",
            "descricao": "Descrição válida com mais de 10 caracteres.",
        },
        {
            "nome": "Ana Maria",
            "email": "email_sem_dominio",
            "telefone": "61999998888",
            "descricao": "Descrição válida com mais de 10 caracteres.",
        },
        {
            "nome": "Ana Maria",
            "email": "ana@email.com",
            "telefone": "12345",
            "descricao": "Descrição válida com mais de 10 caracteres.",
        },
        {
            "nome": "Ana Maria",
            "email": "ana@email.com",
            "telefone": "61999998888",
            "descricao": "Curto",
        },
    ],
)
def test_registrar_solicitacao_endpoint_payloads_invalidos(
    client: TestClient, payload_corrompido: dict
):
    resposta = client.post("/solicitacoes", json=payload_corrompido)

    assert resposta.status_code == 422


def test_registrar_solicitacao_rate_limit(client: TestClient):
    payload = {
        "nome": "Roberto Alves",
        "email": "roberto@email.com",
        "telefone": "61977776666",
        "descricao": "Solicitação para teste de limite de requisições por minuto.",
    }

    respostas = [client.post("/solicitacoes", json=payload) for _ in range(6)]

    assert respostas[-1].status_code == 429
