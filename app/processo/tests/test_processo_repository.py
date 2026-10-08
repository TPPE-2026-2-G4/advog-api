from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.cargo.model import Cargo
from app.cliente.model import Cliente
from app.funcionario.model import Funcionario, StatusFuncionario
from app.processo.model import Processo, StatusProcesso
from app.processo.repository import ProcessoRepository


@pytest.fixture
def dados_base(db_session: Session):
    cargo = Cargo(
        nome_cargo="Advogado",
        descricao="Cargo de teste",
        permissao={},
    )

    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)

    funcionario = Funcionario(
        nome="Funcionário Teste",
        email="funcionario@teste.com",
        status=StatusFuncionario.ATIVO,
        cargo_id=cargo.cargo_id,
    )

    cliente = Cliente(
        nome="Cliente Teste",
        telefone="61999999999",
        email="cliente@teste.com",
        area_interesse="Civil",
        ultima_interacao=datetime(2026, 1, 1),
        responsavel_id=None,
        etapa_id=1,
    )

    db_session.add_all([funcionario, cliente])
    db_session.commit()

    db_session.refresh(funcionario)
    db_session.refresh(cliente)

    return {
        "funcionario": funcionario,
        "cliente": cliente,
    }


@pytest.fixture
def processo(dados_base, db_session):
    processo = Processo(
        cnj="11111111111111111111",
        titulo="Processo Teste",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        data_inicio=datetime(2026, 1, 1),
        data_realizado=None,
        data_prazo=datetime(2026, 12, 31),
        cliente_id=dados_base["cliente"].cliente_id,
        funcionario_id=dados_base["funcionario"].funcionario_id,
    )

    db_session.add(processo)
    db_session.commit()
    db_session.refresh(processo)

    return processo


def buscar_com_filtro(repository, **filtros):
    return repository.buscar_paginado_por_filtros(
        page=1,
        page_size=10,
        **filtros,
    )


def test_buscar_todos(db_session, processo):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_todos()

    assert len(resultado) == 1
    assert resultado[0].processo_id == processo.processo_id


def test_buscar_por_id_encontra_processo(db_session, processo):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_por_id(processo.processo_id)

    assert resultado is not None
    assert resultado.processo_id == processo.processo_id


def test_buscar_por_id_nao_encontra_processo(db_session):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_por_id(999999)

    assert resultado is None


def test_buscar_por_cnj_encontra_processo(db_session, processo):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_por_cnj(processo.cnj)

    assert resultado is not None
    assert resultado.processo_id == processo.processo_id


def test_buscar_por_cnj_nao_encontra_processo(db_session):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_por_cnj("99999999999999999999")

    assert resultado is None


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("cnj", "1111111111"),
        ("titulo", "Processo"),
        ("descricao", "Descrição"),
        ("tribunal", "TJSP"),
        ("area", "Civil"),
    ],
)
def test_buscar_por_filtros_textuais(
    db_session,
    processo,
    campo,
    valor,
):
    repository = ProcessoRepository(db_session)

    itens, total = buscar_com_filtro(repository, **{campo: valor})

    assert total == 1
    assert len(itens) == 1
    assert itens[0].processo_id == processo.processo_id


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("processo_id", "processo_id"),
        ("cliente_id", "cliente_id"),
        ("funcionario_id", "funcionario_id"),
    ],
)
def test_buscar_por_filtros_ids(
    db_session,
    processo,
    campo,
    valor,
):
    repository = ProcessoRepository(db_session)

    valores = {
        "processo_id": processo.processo_id,
        "cliente_id": processo.cliente_id,
        "funcionario_id": processo.funcionario_id,
    }

    itens, total = buscar_com_filtro(
        repository,
        **{campo: valores[valor]},
    )

    assert total == 1
    assert len(itens) == 1
    assert itens[0].processo_id == processo.processo_id


@pytest.mark.parametrize(
    "status",
    [
        StatusProcesso.EM_ANALISE,
        StatusProcesso.ATIVO,
        StatusProcesso.CONCLUIDO,
        StatusProcesso.ARQUIVADO,
    ],
)
def test_buscar_por_status(db_session, dados_base, status):
    processo = Processo(
        cnj=f"{list(StatusProcesso).index(status) + 2:020d}",
        titulo="Processo",
        status=status,
        tribunal="TJSP",
        area="Civil",
        cliente_id=dados_base["cliente"].cliente_id,
        funcionario_id=dados_base["funcionario"].funcionario_id,
    )

    db_session.add(processo)
    db_session.commit()

    repository = ProcessoRepository(db_session)

    itens, total = buscar_com_filtro(
        repository,
        status=status,
    )

    assert total == 1
    assert len(itens) == 1
    assert itens[0].status == status


def test_buscar_por_filtros_sem_resultado(db_session):
    repository = ProcessoRepository(db_session)

    itens, total = buscar_com_filtro(
        repository,
        titulo="Não Existe",
    )

    assert itens == []
    assert total == 0


def test_buscar_por_filtros_paginado(db_session, dados_base):
    repository = ProcessoRepository(db_session)

    processos = []

    for i in range(3):
        processo = Processo(
            cnj=f"{i + 1:020d}",
            titulo=f"Processo {i + 1}",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=dados_base["cliente"].cliente_id,
            funcionario_id=dados_base["funcionario"].funcionario_id,
        )
        db_session.add(processo)
        processos.append(processo)

    db_session.commit()

    itens, total = repository.buscar_paginado_por_filtros(
        page=1,
        page_size=2,
    )

    assert total == 3
    assert len(itens) == 2


def test_buscar_por_filtros_pagina_alem_do_fim(db_session, processo):
    repository = ProcessoRepository(db_session)

    itens, total = repository.buscar_paginado_por_filtros(
        page=100,
        page_size=10,
    )

    assert total == 1
    assert itens == []


def test_criar(db_session, dados_base):
    repository = ProcessoRepository(db_session)

    processo = Processo(
        cnj="22222222222222222222",
        titulo="Novo Processo",
        status=StatusProcesso.EM_ANALISE,
        tribunal="TRF1",
        area="Tributária",
        cliente_id=dados_base["cliente"].cliente_id,
        funcionario_id=dados_base["funcionario"].funcionario_id,
    )

    resultado = repository.criar(processo)

    assert resultado.processo_id is not None
    assert resultado.cnj == "22222222222222222222"


def test_atualizar(db_session, processo):
    repository = ProcessoRepository(db_session)

    processo.titulo = "Título Atualizado"

    resultado = repository.atualizar(processo)

    assert resultado.titulo == "Título Atualizado"


def test_deletar(db_session, processo):
    repository = ProcessoRepository(db_session)

    processo_id = processo.processo_id

    repository.deletar(processo)

    resultado = repository.buscar_por_id(processo_id)

    assert resultado is None
