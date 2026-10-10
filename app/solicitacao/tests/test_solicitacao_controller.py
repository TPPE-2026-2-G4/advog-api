import pytest
from fastapi.testclient import TestClient


def test_registrar_solicitacao_endpoint_sucesso(client: TestClient):
    dados_solicitacao = {
        "nome": "Fernanda Lima",
        "email": "fernanda@email.com",
        "telefone": "(61) 98888-5555",
        "descricao": "Gostaria de agendar uma consulta presencial para tratar de causa trabalhista.",
    }

    resposta = client.post("/solicitacoes", json=dados_solicitacao)

    assert resposta.status_code == 201
    dados_resposta = resposta.json()
    assert dados_resposta["nome"] == "Fernanda Lima"
    assert dados_resposta["email"] == "fernanda@email.com"
    assert dados_resposta["telefone"] == "61988885555"
    assert "id" in dados_resposta


@pytest.mark.parametrize(
    "corpo_requisicao_invalido",
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
def test_registrar_solicitacao_endpoint_dados_invalidos(
    client: TestClient, corpo_requisicao_invalido: dict
):
    resposta = client.post("/solicitacoes", json=corpo_requisicao_invalido)

    assert resposta.status_code == 422


def test_registrar_solicitacao_rate_limit(client: TestClient):
    dados_solicitacao = {
        "nome": "Roberto Alves",
        "email": "roberto@email.com",
        "telefone": "61977776666",
        "descricao": "Solicitação para teste de limite de requisições por minuto.",
    }

    respostas = [client.post("/solicitacoes", json=dados_solicitacao) for _ in range(6)]

    assert respostas[-1].status_code == 429
