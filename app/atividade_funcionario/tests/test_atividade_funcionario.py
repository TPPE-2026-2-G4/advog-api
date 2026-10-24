from datetime import datetime

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from app.atividade.model import Atividade
from app.atividade_funcionario.model import AtividadeFuncionario
from app.etapa_kanban.model import EtapaKanban


def test_vinculo_entre_atividade_e_funcionario_nao_pode_ser_duplicado(
    db_session, funcionario_admin
):
    etapa = EtapaKanban(nome="Backlog", ordem=1)
    db_session.add(etapa)
    db_session.flush()
    atividade = Atividade(
        titulo="Atividade compartilhada",
        descricao="Descrição da atividade",
        data_inicio=datetime(2026, 10, 1),
        data_prazo=datetime(2026, 10, 30),
        etapa_id=etapa.etapa_id,
    )
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
