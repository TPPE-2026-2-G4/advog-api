import pytest
from pydantic import ValidationError

from app.solicitacao.schema import SolicitacaoCreate


@pytest.mark.parametrize(
    "nome_bruto, nome_esperado, email, telefone_bruto, telefone_esperado, descricao",
    [
        (
            "  Carlos Eduardo  ",
            "Carlos Eduardo",
            "carlos@email.com",
            "(61) 99999-8888",
            "61999998888",
            "Necessito de consultoria jurídica em direito civil.",
        ),
        (
            "Maria Souza",
            "Maria Souza",
            "maria.souza@provedor.com.br",
            "61 98888 7777",
            "61988887777",
            "Solicito análise contratual para nova empresa.",
        ),
    ],
)
def test_solicitacao_schema_validos(
    nome_bruto: str,
    nome_esperado: str,
    email: str,
    telefone_bruto: str,
    telefone_esperado: str,
    descricao: str,
):
    schema = SolicitacaoCreate(
        nome=nome_bruto,
        email=email,
        telefone=telefone_bruto,
        descricao=descricao,
    )

    assert schema.nome == nome_esperado
    assert schema.telefone == telefone_esperado
    assert schema.email == email


@pytest.mark.parametrize(
    "payload_invalido",
    [
        {
            "nome": "An",
            "email": "ana@email.com",
            "telefone": "61999998888",
            "descricao": "Descrição válida de serviço.",
        },
        {
            "nome": "João Silva",
            "email": "email-invalido-sem-arroba",
            "telefone": "61999998888",
            "descricao": "Descrição válida de serviço.",
        },
        {
            "nome": "João Silva",
            "email": "joao@email.com",
            "telefone": "123",
            "descricao": "Descrição válida de serviço.",
        },
        {
            "nome": "João Silva",
            "email": "joao@email.com",
            "telefone": "61999998888",
            "descricao": "Curto",
        },
    ],
)
def test_solicitacao_schema_invalidos(payload_invalido: dict):
    with pytest.raises(ValidationError):
        SolicitacaoCreate(**payload_invalido)
