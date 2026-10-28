import pytest
from sqlalchemy.exc import IntegrityError

from app.cliente_arquivo.model import ClienteArquivo


def test_chave_primaria_composta_impede_vinculo_duplicado(db_session):
    db_session.add(ClienteArquivo(cliente_id=1, arquivo_id=1))
    db_session.add(ClienteArquivo(cliente_id=1, arquivo_id=2))
    db_session.add(ClienteArquivo(cliente_id=2, arquivo_id=1))
    db_session.commit()
    assert db_session.query(ClienteArquivo).count() == 3

    db_session.add(ClienteArquivo(cliente_id=1, arquivo_id=1))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
