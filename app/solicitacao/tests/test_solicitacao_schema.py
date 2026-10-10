import pytest
from pydantic import ValidationError

from app.solicitacao.schema import SolicitacaoCreate


@pytest.mark.parametrize(
    "nome, email, telefone, descricao, nome_esperado, telefone_esperado",
    [
        (
            "Ana",
            "ana@email.com",
            "6133334444",
            "1234567890",
            "Ana",
            "6133334444",
        ),
        (
            "A" * 100,
            "limite.superior@email.com",
            "(61) 99999-8888",
            "D" * 2000,
            "A" * 100,
            "61999998888",
        ),
        (
            "   Carlos Eduardo   ",
            "carlos@email.com",
            "(61) 98888-7777",
            "Descrição detalhada da solicitação de serviço.",
            "Carlos Eduardo",
            "61988887777",
        ),
    ],
)
def test_solicitacao_schema_valores_limite_validos(
    nome: str,
    email: str,
    telefone: str,
    descricao: str,
    nome_esperado: str,
    telefone_esperado: str,
):
    schema = SolicitacaoCreate(
        nome=nome,
        email=email,
        telefone=telefone,
        descricao=descricao,
    )

    assert schema.nome == nome_esperado
    assert schema.email == email
    assert schema.telefone == telefone_esperado
    assert len(schema.descricao) == len(descricao)


@pytest.mark.parametrize(
    "payload_invalido",
    [
        {
            "nome": "An",
            "email": "ana@email.com",
            "telefone": "61999998888",
            "descricao": "Descrição válida com mais de 10 caracteres.",
        },
        {
            "nome": "A" * 101,
            "email": "ana@email.com",
            "telefone": "61999998888",
            "descricao": "Descrição válida com mais de 10 caracteres.",
        },
        {
            "nome": "Carlos Silva",
            "email": "carlos@email.com",
            "telefone": "619999988",
            "descricao": "Descrição válida com mais de 10 caracteres.",
        },
        {
            "nome": "Carlos Silva",
            "email": "carlos@email.com",
            "telefone": "1234567890123",
            "descricao": "Descrição válida com mais de 10 caracteres.",
        },
        {
            "nome": "Carlos Silva",
            "email": "carlos@email.com",
            "telefone": "61999998888",
            "descricao": "123456789",
        },
        {
            "nome": "Carlos Silva",
            "email": "carlos@email.com",
            "telefone": "61999998888",
            "descricao": "D" * 2001,
        },
        {
            "nome": "Carlos Silva",
            "email": "email_sem_arroba.com",
            "telefone": "61999998888",
            "descricao": "Descrição válida com mais de 10 caracteres.",
        },
    ],
)
def test_solicitacao_schema_valores_limite_invalidos(payload_invalido: dict):
    with pytest.raises(ValidationError):
        SolicitacaoCreate(**payload_invalido)


def test_solicitacao_schema_cobertura_decisao_tipos_nao_string():
    with pytest.raises(ValidationError):
        SolicitacaoCreate(
            nome=12345,  # type: ignore
            email="teste@email.com",
            telefone=61999998888,  # type: ignore
            descricao="Descrição válida de serviço.",
        )
