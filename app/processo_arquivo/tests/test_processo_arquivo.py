import pytest
from sqlalchemy.exc import IntegrityError

from app.processo_arquivo.model import ProcessoArquivo


def test_chave_primaria_composta_impede_vinculo_duplicado(db_session):
    db_session.add(ProcessoArquivo(processo_id=1, arquivo_id=1))
    db_session.add(ProcessoArquivo(processo_id=1, arquivo_id=2))
    db_session.add(ProcessoArquivo(processo_id=2, arquivo_id=1))
    db_session.commit()
    assert db_session.query(ProcessoArquivo).count() == 3

    db_session.add(ProcessoArquivo(processo_id=1, arquivo_id=1))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
