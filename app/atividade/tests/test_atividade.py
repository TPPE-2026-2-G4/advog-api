import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError

from app.atividade.model import Atividade, AtividadeFuncionario, EtapaKanban
from app.atividade.seed import ETAPAS_PADRAO, inicializar_etapas_kanban


@pytest.mark.parametrize("nome_existente", [None, "Backlog", "Personalizada"])
def test_inicializar_etapas_preserva_existentes_e_nao_duplica(db_session, nome_existente):
    db_session.execute(delete(EtapaKanban))
    if nome_existente is not None:
        db_session.add(EtapaKanban(nome=nome_existente, ordem=10))
    db_session.commit()

    for _ in range(2):
        inicializar_etapas_kanban(db_session)
        db_session.commit()

    etapas = {etapa.nome: etapa.ordem for etapa in db_session.scalars(select(EtapaKanban))}
    esperado = {nome: ordem for ordem, nome in enumerate(ETAPAS_PADRAO, start=1)}
    if nome_existente is not None:
        esperado[nome_existente] = 10

    assert etapas == esperado
    assert db_session.query(EtapaKanban).count() == len(esperado)
    assert db_session.query(Atividade).count() == 0


def test_vinculo_entre_atividade_e_funcionario_nao_pode_ser_duplicado(
    db_session, funcionario_admin
):
    etapa = EtapaKanban(nome="Backlog", ordem=1)
    db_session.add(etapa)
    db_session.flush()
    atividade = Atividade(titulo="Atividade compartilhada", etapa_id=etapa.etapa_id)
    db_session.add(atividade)
    db_session.flush()
    vinculo = {
        "atividade_id": atividade.atividade_id,
        "funcionario_id": funcionario_admin.funcionario_id,
    }
    db_session.execute(insert(AtividadeFuncionario).values(**vinculo))
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(insert(AtividadeFuncionario).values(**vinculo))
    db_session.rollback()
