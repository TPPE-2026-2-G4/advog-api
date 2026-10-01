import pytest
from app.processo.repository import ProcessoRepository
from app.processo.model import Processo


def test_find_all_by_descricao(db_session):
    repo = ProcessoRepository(db_session)
    p1 = Processo(titulo_proc="T1", descricao_proc="Um processo muito complexo")
    p2 = Processo(titulo_proc="T2", descricao_proc="Nada demais")
    repo.save(p1)
    repo.save(p2)

    resultados = repo.find_all_by_filters(descricao_proc="complexo")

    assert len(resultados) == 1
    assert resultados[0].titulo_proc == "T1"
