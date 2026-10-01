from datetime import datetime
from unittest.mock import patch

import pytest

from app.config.database import Base, SessionLocal, engine
from app.processo.model import Processo
from app.processo.service import ProcessoService


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.rollback()
    db.query(Processo).delete()
    db.commit()
    db.close()


@pytest.mark.asyncio
@patch("app.processo.service.JusbrasilApiClient.fetch_processo")
async def test_sincronizar_processos_com_api(mock_fetch, db_session):
    p1 = Processo(cnj="123456789", titulo_proc="Proc 1", status="Em Andamento")
    p2 = Processo(cnj=None, titulo_proc="Proc sem CNJ", status="Em Andamento")

    db_session.add(p1)
    db_session.add(p2)
    db_session.commit()

    mock_data = {
        "status": "Concluído",
        "tribunal": "TJSP",
        "data_realizado": datetime(2026, 12, 1),
    }
    mock_fetch.return_value = mock_data

    await ProcessoService.sincronizar_processos_com_api()

    db_session.refresh(p1)
    assert p1.status == "Concluído"
    assert p1.tribunal == "TJSP"
    assert p1.data_realizado == mock_data["data_realizado"]

    db_session.refresh(p2)
    assert p2.status == "Em Andamento"

    mock_fetch.assert_called_once_with("123456789")


@pytest.mark.asyncio
@patch("app.processo.service.JusbrasilApiClient.fetch_processo")
async def test_sincronizar_processos_com_api_empty_cnj(mock_fetch, db_session):
    p1 = Processo(cnj="", titulo_proc="Proc vazio", status="Em Andamento")
    db_session.add(p1)
    db_session.commit()

    await ProcessoService.sincronizar_processos_com_api()
    mock_fetch.assert_not_called()


@pytest.mark.asyncio
@patch("app.processo.service.JusbrasilApiClient.fetch_processo")
async def test_sincronizar_processos_com_api_exception(mock_fetch, db_session):
    p1 = Processo(cnj="123", titulo_proc="Proc", status="Em Andamento")
    db_session.add(p1)
    db_session.commit()

    mock_fetch.side_effect = Exception("Erro forçado")

    await ProcessoService.sincronizar_processos_com_api()

    db_session.refresh(p1)
    assert p1.status == "Em Andamento"
