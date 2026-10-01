import pytest
from app.cliente.repository import ClienteRepository
from app.cliente.model import Cliente
from app.cliente.schema import ClienteCreate
from datetime import datetime, timezone


def test_update_cliente_existente(db_session):
    repo = ClienteRepository(db_session)
    novo_cliente_data = ClienteCreate(
        nome="Cliente Teste",
        telefone="11999999999",
        email="cliente@teste.com",
        ultima_interacao=datetime.now(timezone.utc),
        etapa_id=1,
    )
    cliente = repo.create(novo_cliente_data)

    # Testa update
    atualizado = repo.update(cliente.cliente_id, {"nome": "Nome Atualizado"})
    assert atualizado is not None
    assert atualizado.nome == "Nome Atualizado"


def test_update_cliente_inexistente(db_session):
    repo = ClienteRepository(db_session)
    atualizado = repo.update(999, {"nome": "Nome Atualizado"})
    assert atualizado is None


def test_delete_cliente_existente(db_session):
    repo = ClienteRepository(db_session)
    novo_cliente_data = ClienteCreate(
        nome="Cliente Teste",
        telefone="11999999999",
        email="cliente@teste.com",
        ultima_interacao=datetime.now(timezone.utc),
        etapa_id=1,
    )
    cliente = repo.create(novo_cliente_data)

    # Testa delete
    sucesso = repo.delete(cliente.cliente_id)
    assert sucesso is True

    # Verifica se realmente deletou
    assert repo.get_by_id(cliente.cliente_id) is None


def test_delete_cliente_inexistente(db_session):
    repo = ClienteRepository(db_session)
    sucesso = repo.delete(999)
    assert sucesso is False
