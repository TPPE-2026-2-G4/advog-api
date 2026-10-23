from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.cargo.model import Cargo
from app.cliente.model import Cliente
from app.funcionario.model import Funcionario, StatusFuncionario
from app.processo.model import DocumentoProcesso, Processo, StatusProcesso
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


def test_buscar_por_filtros_busca_textual_e_datas_prazo(db_session, processo):
    repository = ProcessoRepository(db_session)

    itens_busca, total_busca = repository.buscar_paginado_por_filtros(
        page=1,
        page_size=10,
        busca=processo.titulo,
    )
    assert total_busca == 1
    assert len(itens_busca) == 1

    prazo_data = processo.data_prazo.date()
    itens_prazo, total_prazo = repository.buscar_paginado_por_filtros(
        page=1,
        page_size=10,
        prazo_inicio=prazo_data,
        prazo_fim=prazo_data,
    )
    assert total_prazo == 1
    assert len(itens_prazo) == 1


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


@pytest.mark.parametrize(
    "status,data_realizado,data_inicio,func_vinculo,dias_filtro,func_filtro,espera_critico",
    [
        (StatusProcesso.ATIVO, None, datetime.now(UTC) - timedelta(days=40), True, 30, None, True),
        (
            StatusProcesso.ATIVO,
            datetime.now(UTC) - timedelta(days=5),
            datetime.now(UTC) - timedelta(days=40),
            True,
            30,
            None,
            False,
        ),
        (
            StatusProcesso.ATIVO,
            datetime.now(UTC) - timedelta(days=45),
            datetime.now(UTC) - timedelta(days=100),
            True,
            30,
            None,
            True,
        ),
        (
            StatusProcesso.CONCLUIDO,
            None,
            datetime.now(UTC) - timedelta(days=50),
            True,
            30,
            None,
            False,
        ),
        (
            StatusProcesso.ARQUIVADO,
            None,
            datetime.now(UTC) - timedelta(days=50),
            True,
            30,
            None,
            False,
        ),
        (StatusProcesso.ATIVO, None, datetime.now(UTC) - timedelta(days=40), False, 30, 999, False),
        (StatusProcesso.ATIVO, None, datetime.now(UTC) - timedelta(days=40), True, 30, True, True),
        (StatusProcesso.ATIVO, None, datetime.now(UTC) - timedelta(days=15), True, 10, None, True),
        (StatusProcesso.ATIVO, None, None, True, 30, None, True),
    ],
)
def test_buscar_por_filtros_atividade_e_status_excluidos(
    db_session,
    dados_base,
    status,
    data_realizado,
    data_inicio,
    func_vinculo,
    dias_filtro,
    func_filtro,
    espera_critico,
):
    repository = ProcessoRepository(db_session)
    funcionario = dados_base["funcionario"]
    cliente = dados_base["cliente"]

    funcionario_id = funcionario.funcionario_id if func_vinculo else None

    proc = Processo(
        cnj="99999999999999999999",
        titulo="Processo Teste Crítico",
        status=status,
        tribunal="TJDFT",
        area="Trabalhista",
        cliente_id=cliente.cliente_id,
        funcionario_id=funcionario_id,
        data_realizado=data_realizado,
        data_inicio=data_inicio,
    )
    repository.criar(proc)

    filtro_func = funcionario.funcionario_id if func_filtro is True else func_filtro

    criticos = repository.buscar_por_filtros(
        status_excluidos=[StatusProcesso.CONCLUIDO, StatusProcesso.ARQUIVADO],
        ultima_atividade_ate=datetime.now(UTC) - timedelta(days=dias_filtro),
        funcionario_id=filtro_func,
    )

    if espera_critico:
        assert any(p.processo_id == proc.processo_id for p in criticos)
    else:
        assert not any(p.processo_id == proc.processo_id for p in criticos)


def test_documento_repository_crud(db_session: Session, dados_base: dict):
    repository = ProcessoRepository(db_session)
    cliente = dados_base["cliente"]
    funcionario = dados_base["funcionario"]

    proc = Processo(
        cnj="88888888888888888888",
        titulo="Processo com Documento",
        status=StatusProcesso.ATIVO,
        tribunal="TJDFT",
        area="Civil",
        cliente_id=cliente.cliente_id,
        funcionario_id=funcionario.funcionario_id,
    )
    repository.criar(proc)

    docs = repository.listar_documentos(proc.processo_id)
    assert docs == []

    # Adicionar documento
    doc = DocumentoProcesso(
        processo_id=proc.processo_id,
        nome_original="peticao.pdf",
        chave_minio=f"processos/{proc.processo_id}/peticao.pdf",
        origem="manual",
        tamanho_bytes=2048,
        entrada_tipo="application/pdf",
        funcionario_id=funcionario.funcionario_id,
    )
    doc_salvo = repository.adicionar_documento(doc)
    assert doc_salvo.documento_id is not None
    assert doc_salvo.nome_original == "peticao.pdf"
    assert doc_salvo.origem == "manual"

    doc_encontrado = repository.buscar_documento_por_id(doc_salvo.documento_id)
    assert doc_encontrado is not None
    assert doc_encontrado.chave_minio == doc.chave_minio

    assert repository.buscar_documento_por_id(999999) is None

    docs_listados = repository.listar_documentos(proc.processo_id)
    assert len(docs_listados) == 1
    assert docs_listados[0].documento_id == doc_salvo.documento_id

    repository.deletar_documento(doc_salvo)
    assert repository.buscar_documento_por_id(doc_salvo.documento_id) is None
    assert repository.listar_documentos(proc.processo_id) == []
