import pytest
from sqlalchemy import select

from app.atividade.model import EtapaKanban
from app.atividade.seed import inicializar_etapas_kanban
from app.funcionario.model import Funcionario, StatusFuncionario


@pytest.fixture
def etapas(db_session):
    inicializar_etapas_kanban(db_session)
    db_session.flush()
    return {etapa.nome: etapa for etapa in db_session.scalars(select(EtapaKanban))}


@pytest.fixture
def funcionarios(db_session, cargo_padrao):
    usuarios = [
        Funcionario(
            nome=f"Funcionário {indice}",
            email=f"dashboard{indice}@teste.com",
            status=StatusFuncionario.ATIVO,
            cargo=cargo_padrao,
        )
        for indice in range(2)
    ]
    db_session.add_all(usuarios)
    db_session.flush()
    return usuarios
