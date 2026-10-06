from unittest.mock import MagicMock

import pytest

from app.processo.model import Processo, StatusProcesso
from app.processo.schema import ProcessoCreate, ProcessoFilter, ProcessoUpdate
from app.processo.service import ProcessoService


def criar_service():
    db = MagicMock()
    service = ProcessoService(db)
    service.repository = MagicMock()
    return service


def dados_processo_create() -> ProcessoCreate:
    return ProcessoCreate(
        cnj="11111111111111111111",
        titulo="Processo Teste",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=1,
        funcionario_id=2,
    )


def test_buscar_todos():
    service = criar_service()

    processos = [MagicMock(spec=Processo)]

    service.repository.buscar_todos.return_value = processos

    resultado = service.buscar_todos()

    assert resultado == processos
    service.repository.buscar_todos.assert_called_once()


def test_buscar_processos():
    service = criar_service()

    filtros = ProcessoFilter(
        processo_id=None,
        cnj=None,
        titulo="Teste",
        descricao=None,
        status=StatusProcesso.ATIVO,
        tribunal=None,
        area=None,
        cliente_id=1,
        funcionario_id=2,
    )

    processos = [MagicMock(spec=Processo)]
    service.repository.buscar_por_filtros.return_value = processos

    resultado = service.buscar_processos(filtros)

    assert resultado == processos

    service.repository.buscar_por_filtros.assert_called_once_with(
        processo_id=None,
        cnj=None,
        titulo="Teste",
        descricao=None,
        status=StatusProcesso.ATIVO,
        tribunal=None,
        area=None,
        cliente_id=1,
        funcionario_id=2,
    )


def test_criar_processo():
    service = criar_service()

    dados = dados_processo_create()

    service.repository.buscar_por_cnj.return_value = None

    processo_criado = MagicMock(spec=Processo)
    service.repository.criar.return_value = processo_criado

    resultado = service.criar_processo(dados)

    assert resultado == processo_criado

    service.repository.buscar_por_cnj.assert_called_once_with(dados.cnj)
    service.repository.criar.assert_called_once()


def test_criar_processo_com_cnj_existente():
    service = criar_service()

    dados = dados_processo_create()

    processo_existente = MagicMock(spec=Processo)

    service.repository.buscar_por_cnj.return_value = processo_existente

    with pytest.raises(ValueError, match="Processo já cadastrado"):
        service.criar_processo(dados)

    service.repository.criar.assert_not_called()


def test_atualizar_processo():
    service = criar_service()

    processo = MagicMock(spec=Processo)
    processo.processo_id = 1

    dados = ProcessoUpdate(
        titulo="Novo título",
        status=StatusProcesso.CONCLUIDO,
        funcionario_id=10,
    )

    service.repository.buscar_por_id.return_value = processo
    service.repository.buscar_por_cnj.return_value = None
    service.repository.atualizar.return_value = processo

    resultado = service.atualizar_processo(1, dados)

    assert resultado == processo

    assert processo.titulo == "Novo título"
    assert processo.status == StatusProcesso.CONCLUIDO
    assert processo.funcionario_id == 10

    service.repository.atualizar.assert_called_once_with(processo)


def test_atualizar_processo_inexistente():
    service = criar_service()

    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.atualizar_processo(
            999,
            ProcessoUpdate(titulo="Teste"),
        )

    service.repository.atualizar.assert_not_called()


def test_atualizar_processo_com_cnj_duplicado():
    service = criar_service()

    processo_atual = MagicMock(spec=Processo)
    processo_atual.processo_id = 1

    outro_processo = MagicMock(spec=Processo)
    outro_processo.processo_id = 2

    service.repository.buscar_por_id.return_value = processo_atual
    service.repository.buscar_por_cnj.return_value = outro_processo

    with pytest.raises(ValueError, match="CNJ já cadastrado"):
        service.atualizar_processo(
            1,
            ProcessoUpdate(
                cnj="22222222222222222222",
            ),
        )

    service.repository.atualizar.assert_not_called()


def test_atualizar_processo_com_mesmo_cnj():
    service = criar_service()

    processo = MagicMock(spec=Processo)
    processo.processo_id = 1

    service.repository.buscar_por_id.return_value = processo
    service.repository.buscar_por_cnj.return_value = processo
    service.repository.atualizar.return_value = processo

    resultado = service.atualizar_processo(
        1,
        ProcessoUpdate(
            cnj="11111111111111111111",
        ),
    )

    assert resultado == processo
    service.repository.atualizar.assert_called_once_with(processo)


def test_deletar_processo():
    service = criar_service()

    processo = MagicMock(spec=Processo)

    service.repository.buscar_por_id.return_value = processo

    service.deletar_processo(1)

    service.repository.deletar.assert_called_once_with(processo)


def test_deletar_processo_inexistente():
    service = criar_service()

    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.deletar_processo(999)

    service.repository.deletar.assert_not_called()
