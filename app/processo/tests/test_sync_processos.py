from datetime import datetime
from unittest.mock import patch

import pytest

from app.cliente.model import Cliente
from app.config.database import Base, SessionLocal, engine
from app.processo.model import Processo, StatusProcesso
from app.processo.service import ProcessoService


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    cliente = Cliente(
        nome="Cliente Sync",
        telefone="11999999999",
        email="sync@teste.com",
        area_interesse="Civil",
        etapa_id=1,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    yield db, cliente

    db.rollback()
    db.query(Processo).delete()
    db.query(Cliente).delete()
    db.commit()
    db.close()


@pytest.mark.asyncio
@patch("app.processo.service.DatajudApiClient.fetch_processo")
async def test_sincronizar_processos_com_api(mock_fetch, db_session):
    db, cliente = db_session
    p1 = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        funcionario_id=1,
        cnj="123456789",
        titulo="Proc 1",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )
    p2 = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        funcionario_id=1,
        cnj="987654321",
        titulo="Proc 2",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )

    db.add(p1)
    db.add(p2)
    db.commit()

    mock_data = {
        "status": StatusProcesso.CONCLUIDO,
        "tribunal": "TJSP",
        "data_realizado": datetime(2026, 12, 1),
    }

    async def side_effect(cnj):
        if cnj == "123456789":
            return mock_data
        return None

    mock_fetch.side_effect = side_effect

    await ProcessoService.sincronizar_processos_com_api()

    db.refresh(p1)
    assert p1.status == StatusProcesso.CONCLUIDO
    assert p1.tribunal == "TJSP"
    assert p1.data_realizado == mock_data["data_realizado"]

    db.refresh(p2)
    assert p2.status == StatusProcesso.ATIVO


@pytest.mark.asyncio
@patch("app.processo.service.DatajudApiClient.fetch_processo")
async def test_sincronizar_processos_com_api_empty_cnj(mock_fetch, db_session):
    db, cliente = db_session
    p1 = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        funcionario_id=1,
        cnj=" ",
        titulo="Proc vazio",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )
    p1.cnj = ""
    db.add(p1)
    db.commit()

    await ProcessoService.sincronizar_processos_com_api()
    mock_fetch.assert_not_called()


@pytest.mark.asyncio
@patch("app.processo.service.DatajudApiClient.fetch_processo")
async def test_sincronizar_processos_com_api_exception(mock_fetch, db_session):
    db, cliente = db_session
    p1 = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        funcionario_id=1,
        cnj="123",
        titulo="Proc",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )
    db.add(p1)
    db.commit()

    mock_fetch.side_effect = Exception("Erro forçado")

    with pytest.raises(Exception, match="Erro forçado"):
        await ProcessoService.sincronizar_processos_com_api()

    db.refresh(p1)
    assert p1.status == StatusProcesso.ATIVO
