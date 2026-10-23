from datetime import UTC, datetime, timedelta
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
        busca=None,
        prazo_inicio=None,
        prazo_fim=None,
        page=1,
        page_size=10,
    )

    processo = Processo(
        processo_id=1,
        cnj="11111111111111111111",
        titulo="Processo Teste",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=1,
        funcionario_id=2,
    )

    service.repository.buscar_paginado_por_filtros.return_value = ([processo], 1)

    resultado = service.buscar_processos(filtros)

    assert resultado.total == 1
    assert resultado.page == 1
    assert resultado.page_size == 10
    assert resultado.total_pages == 1
    assert len(resultado.itens) == 1
    assert resultado.itens[0].processo_id == processo.processo_id

    service.repository.buscar_paginado_por_filtros.assert_called_once_with(
        page=1,
        page_size=10,
        processo_id=None,
        cnj=None,
        titulo="Teste",
        descricao=None,
        status=StatusProcesso.ATIVO,
        tribunal=None,
        area=None,
        cliente_id=1,
        funcionario_id=2,
        busca=None,
        prazo_inicio=None,
        prazo_fim=None,
    )


def test_buscar_processos_com_paginacao():
    service = criar_service()

    filtros = ProcessoFilter(
        processo_id=None,
        cnj=None,
        titulo=None,
        descricao=None,
        status=None,
        tribunal=None,
        area=None,
        cliente_id=None,
        funcionario_id=None,
        busca=None,
        prazo_inicio=None,
        prazo_fim=None,
        page=2,
        page_size=5,
    )

    processos = [
        Processo(
            processo_id=6,
            cnj="66666666666666666666",
            titulo="Processo 6",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=1,
        ),
        Processo(
            processo_id=7,
            cnj="77777777777777777777",
            titulo="Processo 7",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=1,
        ),
    ]

    service.repository.buscar_paginado_por_filtros.return_value = (processos, 12)

    resultado = service.buscar_processos(filtros)

    assert resultado.total == 12
    assert resultado.page == 2
    assert resultado.page_size == 5
    assert resultado.total_pages == 3
    assert len(resultado.itens) == 2


def test_buscar_processos_sem_resultado():
    service = criar_service()

    filtros = ProcessoFilter(
        processo_id=None,
        cnj=None,
        titulo="Não Existe",
        descricao=None,
        status=None,
        tribunal=None,
        area=None,
        cliente_id=None,
        funcionario_id=None,
        busca=None,
        prazo_inicio=None,
        prazo_fim=None,
        page=1,
        page_size=10,
    )

    service.repository.buscar_paginado_por_filtros.return_value = ([], 0)

    resultado = service.buscar_processos(filtros)

    assert resultado.itens == []
    assert resultado.total == 0
    assert resultado.page == 1
    assert resultado.page_size == 10
    assert resultado.total_pages == 1


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


@pytest.mark.parametrize(
    "dias,func_id",
    [
        (30, None),
        (15, 1),
        (60, 2),
        (0, None),
    ],
)
def test_buscar_processos_criticos_parametrizado(dias, func_id):
    service = criar_service()
    processos = [
        Processo(
            processo_id=1,
            cnj="11111111111111111111",
            titulo="Proc Crítico",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=1,
            funcionario_id=func_id,
        )
    ]
    service.repository.buscar_por_filtros.return_value = processos

    antes = datetime.now(UTC) - timedelta(days=dias)
    resultado = service.buscar_processos_criticos(
        dias_sem_movimentacao=dias,
        funcionario_id=func_id,
    )
    depois = datetime.now(UTC) - timedelta(days=dias)

    assert len(resultado) == 1
    assert resultado[0].processo_id == 1
    assert resultado[0].cnj == "11111111111111111111"
    service.repository.buscar_por_filtros.assert_called_once()
    kwargs = service.repository.buscar_por_filtros.call_args.kwargs
    assert kwargs["status_excluidos"] == [StatusProcesso.CONCLUIDO, StatusProcesso.ARQUIVADO]
    assert kwargs["funcionario_id"] == func_id
    assert antes <= kwargs["ultima_atividade_ate"] <= depois


@pytest.mark.parametrize(
    "nome_cargo,permissoes,sem_cargo,usuario_nulo,esperado",
    [
        ("Administrador", {}, False, False, True),
        ("  admin ", {}, False, False, True),
        ("Advogado Sênior", {"configuracoes_sistema": True}, False, False, True),
        ("Advogado Pleno", {"visualizar_processos": True}, False, False, False),
        ("", None, True, False, False),
        ("", None, False, True, True),
    ],
)
def test_eh_administrador_parametrizado(
    nome_cargo,
    permissoes,
    sem_cargo,
    usuario_nulo,
    esperado,
):
    if usuario_nulo:
        usuario = None
    else:
        usuario = MagicMock()
        if sem_cargo:
            usuario.cargo = None
        else:
            cargo = MagicMock()
            cargo.nome_cargo = nome_cargo
            cargo.permissao = permissoes
            usuario.cargo = cargo

    assert ProcessoService._eh_administrador(usuario) is esperado


@pytest.mark.parametrize(
    "eh_admin,usuario_id,filtro_param,dias_prazo,contagens_status,atrasados_mock,proximos_mock,filtro_esperado",
    [
        (
            True,
            1,
            None,
            7,
            {
                StatusProcesso.ATIVO: 4,
                StatusProcesso.EM_ANALISE: 2,
                StatusProcesso.CONCLUIDO: 3,
                StatusProcesso.ARQUIVADO: 1,
            },
            1,
            2,
            None,
        ),
        (
            True,
            1,
            25,
            15,
            {
                StatusProcesso.ATIVO: 2,
            },
            0,
            1,
            25,
        ),
        (
            False,
            10,
            99,
            7,
            {
                StatusProcesso.EM_ANALISE: 3,
                StatusProcesso.ARQUIVADO: 2,
            },
            2,
            0,
            10,
        ),
    ],
)
def test_obter_resumo_processos_parametrizado(
    eh_admin,
    usuario_id,
    filtro_param,
    dias_prazo,
    contagens_status,
    atrasados_mock,
    proximos_mock,
    filtro_esperado,
):
    service = criar_service()

    usuario = MagicMock()
    usuario.funcionario_id = usuario_id
    cargo = MagicMock()
    cargo.nome_cargo = "Administrador" if eh_admin else "Advogado"
    cargo.permissao = {"configuracoes_sistema": eh_admin}
    usuario.cargo = cargo

    service.repository.contar_por_status.return_value = contagens_status
    service.repository.contar_por_filtros.side_effect = [atrasados_mock, proximos_mock]

    resumo = service.obter_resumo_processos(
        usuario=usuario,
        funcionario_id=filtro_param,
        dias_proximo_prazo=dias_prazo,
    )

    em_andamento_esp = contagens_status.get(StatusProcesso.ATIVO, 0)
    em_analise_esp = contagens_status.get(StatusProcesso.EM_ANALISE, 0)
    finalizados_esp = contagens_status.get(StatusProcesso.CONCLUIDO, 0)

    assert resumo.em_andamento == em_andamento_esp
    assert resumo.em_analise == em_analise_esp
    assert resumo.finalizados == finalizados_esp
    assert resumo.total == em_andamento_esp + em_analise_esp + finalizados_esp
    assert resumo.atrasados == atrasados_mock
    assert resumo.proximos_do_prazo == proximos_mock

    service.repository.contar_por_status.assert_called_once_with(funcionario_id=filtro_esperado)
    assert service.repository.contar_por_filtros.call_count == 2
