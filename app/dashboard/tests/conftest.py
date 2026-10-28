import pytest
from sqlalchemy import select

from app.etapa_kanban.model import EtapaKanban
from app.funcionario.model import Funcionario, StatusFuncionario


@pytest.fixture
def etapas(db_session, etapas_kanban_padrao):
    return {etapa.nome: etapa for etapa in db_session.scalars(select(EtapaKanban))}


@pytest.fixture
def funcionarios(db_session, cargo_padrao):
    usuarios = [
        Funcionario(
            atuacao_id=1,
            foto_perfil=1,
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
