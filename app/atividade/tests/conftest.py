from datetime import datetime

import pytest
from sqlalchemy import select

from app.atividade.model import Atividade
from app.atividade_funcionario.model import AtividadeFuncionario
from app.cliente.model import Cliente
from app.etapa_kanban.model import EtapaKanban
from app.etapa_kanban.seed import inicializar_etapas_kanban
from app.funcionario.model import Funcionario, StatusFuncionario
from app.processo.model import Processo


@pytest.fixture
def etapas(db_session):
    inicializar_etapas_kanban(db_session)
    db_session.add(EtapaKanban(nome="Aguardando cliente", ordem=2))
    db_session.flush()
    return {etapa.nome: etapa for etapa in db_session.scalars(select(EtapaKanban))}


@pytest.fixture
def funcionarios(db_session, cargo_padrao):
    usuarios = [
        Funcionario(
            nome=f"Funcionário {indice}",
            email=f"kanban{indice}@teste.com",
            senha_hash="hash que não deve ser exposto",
            status=StatusFuncionario.ATIVO,
            cargo=cargo_padrao,
        )
        for indice in range(2)
    ]
    db_session.add_all(usuarios)
    db_session.flush()
    return usuarios


@pytest.fixture
def processo(db_session):
    cliente = Cliente(nome="Cliente Kanban", email="cliente.kanban@teste.com")
    db_session.add(cliente)
    db_session.flush()
    processo = Processo(
        cnj="00000000000000000000",
        titulo="Processo Kanban",
        tribunal="TJDFT",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )
    db_session.add(processo)
    db_session.flush()
    return processo


@pytest.fixture
def atividades(db_session, etapas, funcionarios, processo):
    distribuicao = [
        ("propria", "Backlog", [0]),
        ("terceiros", "Em Execução", [1]),
        ("compartilhada", "Revisão", [1, 0]),
        ("sem_responsavel", "Backlog", []),
        ("finalizada", "Finalizado", [0]),
    ]
    atividades = {}
    for titulo, nome_etapa, indices in distribuicao:
        atividade = Atividade(
            titulo=titulo,
            descricao="Descrição da atividade",
            data_inicio=datetime(2026, 10, 1),
            data_prazo=datetime(2026, 10, 30, 15, 30),
            etapa_id=etapas[nome_etapa].etapa_id,
            processo_id=processo.processo_id if titulo == "compartilhada" else None,
        )
        db_session.add(atividade)
        db_session.flush()
        db_session.add_all(
            AtividadeFuncionario(
                atividade_id=atividade.atividade_id,
                funcionario_id=funcionarios[indice].funcionario_id,
            )
            for indice in indices
        )
        atividades[titulo] = atividade
    db_session.commit()
    return atividades
