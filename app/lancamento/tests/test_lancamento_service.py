from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento
from app.lancamento.repository import LancamentoRepository
from app.lancamento.schema import (
    LancamentoCalendarioResponse,
    LancamentoCreate,
    LancamentoFilter,
    LancamentoUpdate,
)
from app.lancamento.service import LancamentoCalendarioService, LancamentoService


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def lancamento_service(mock_db_session):
    service = LancamentoService.__new__(LancamentoService)
    service.repository = MagicMock(spec=LancamentoRepository)
    return service


@pytest.fixture
def calendario_service():
    mock_repo = MagicMock(spec=LancamentoRepository)
    return LancamentoCalendarioService(mock_repo)


class TestLancamentoServiceBuscar:
    def test_buscar_por_id_sucesso(self, lancamento_service):
        lancamento_mock = Lancamento(
            lancamento_id=1,
            titulo="Honorários Iniciais",
            valor=1000.0,
            status=StatusLancamento.PENDENTE,
        )
        lancamento_service.repository.buscar_por_id.return_value = lancamento_mock

        resultado = lancamento_service.buscar_por_id(1)

        assert resultado == lancamento_mock
        lancamento_service.repository.buscar_por_id.assert_called_once_with(1)

    def test_buscar_por_id_inexistente_lanca_erro(self, lancamento_service):
        lancamento_service.repository.buscar_por_id.return_value = None

        with pytest.raises(ValueError, match="Lançamento não encontrado"):
            lancamento_service.buscar_por_id(999)


class TestLancamentoServiceListarEFiltrar:
    @pytest.mark.parametrize(
        "inicio,fim,deve_lancar_erro",
        [
            (date(2026, 10, 10), date(2026, 10, 1), True),
            (date(2026, 10, 1), date(2026, 10, 10), False),
            (date(2026, 10, 1), date(2026, 10, 1), False),
            (None, date(2026, 10, 10), False),
            (date(2026, 10, 1), None, False),
        ],
    )
    def test_validar_periodo(self, lancamento_service, inicio, fim, deve_lancar_erro):
        filtros = LancamentoFilter(inicio=inicio, fim=fim)

        if deve_lancar_erro:
            with pytest.raises(
                ValueError, match="A data inicial não pode ser posterior à data final"
            ):
                lancamento_service.listar_lancamentos(filtros)
        else:
            lancamento_service.repository.buscar_por_filtros.return_value = []
            resultado = lancamento_service.listar_lancamentos(filtros)
            assert isinstance(resultado, list)

    @pytest.mark.parametrize(
        "page,page_size,total,total_pages_esperado",
        [
            (1, 10, 25, 3),
            (1, 10, 10, 1),
            (1, 10, 0, 1),
            (2, 5, 12, 3),
        ],
    )
    def test_listar_lancamentos_paginado_calculo_paginas(
        self, lancamento_service, page, page_size, total, total_pages_esperado
    ):
        filtros = LancamentoFilter(inicio=None, fim=None)
        lancamento_mock = Lancamento(
            lancamento_id=1,
            titulo="Consulta",
            tipo=TipoLancamento.ENTRADA,
            valor=200.0,
            data_vencimento=datetime.now(),
            status=StatusLancamento.PENDENTE,
        )
        itens = [lancamento_mock] if total > 0 else []

        lancamento_service.repository.buscar_paginado.return_value = (itens, total)

        resultado = lancamento_service.listar_lancamentos_paginado(filtros, page, page_size)

        assert resultado.total == total
        assert resultado.page == page
        assert resultado.page_size == page_size
        assert resultado.total_pages == total_pages_esperado

    def test_resolver_periodo_com_dias_calcula_inicio_e_fim_default(self, lancamento_service):
        filtros = LancamentoFilter(dias=7)
        lancamento_service.repository.buscar_por_filtros.return_value = []

        lancamento_service.listar_lancamentos(filtros)

        _, kwargs = lancamento_service.repository.buscar_por_filtros.call_args
        assert kwargs["fim"] == date.today()
        assert kwargs["inicio"] == date.today() - timedelta(days=6)

    def test_resolver_periodo_com_dias_e_fim_especifico(self, lancamento_service):
        data_fim = date(2026, 10, 20)
        filtros = LancamentoFilter(dias=5, fim=data_fim)
        lancamento_service.repository.buscar_por_filtros.return_value = []

        lancamento_service.listar_lancamentos(filtros)

        _, kwargs = lancamento_service.repository.buscar_por_filtros.call_args
        assert kwargs["fim"] == data_fim
        assert kwargs["inicio"] == date(2026, 10, 16)


class TestLancamentoServiceResumo:
    def test_resumir_lancamentos_calcula_totais_corretamente(self, lancamento_service):
        lancamento_service.repository.totais_por_status_e_tipo.return_value = [
            (StatusLancamento.PENDENTE, TipoLancamento.ENTRADA, 2, 1000.0),
            (StatusLancamento.PENDENTE, TipoLancamento.SAIDA, 1, 200.0),
            (StatusLancamento.REALIZADO, TipoLancamento.ENTRADA, 3, 1500.0),
        ]

        filtros = LancamentoFilter(inicio=date(2026, 10, 1), fim=date(2026, 10, 31))
        resumo = lancamento_service.resumir_lancamentos(filtros)

        assert resumo.pendente.quantidade == 3
        assert resumo.pendente.total_entradas == 1000.0
        assert resumo.pendente.total_saidas == 200.0
        assert resumo.realizado.total_entradas == 1500.0


class TestLancamentoServiceCriarEAtualizar:
    @pytest.mark.parametrize(
        "categoria_id,cliente_id,cat_existe,cli_existe,mensagem_esperada",
        [
            (99, None, False, True, "Categoria não encontrada"),
            (None, 88, True, False, "Cliente não encontrado"),
            (99, 88, False, False, "Categoria não encontrada"),
        ],
    )
    def test_validar_referencias_invalidas_lanca_erro(
        self,
        lancamento_service,
        categoria_id,
        cliente_id,
        cat_existe,
        cli_existe,
        mensagem_esperada,
    ):
        lancamento_service.repository.categoria_existe.return_value = cat_existe
        lancamento_service.repository.cliente_existe.return_value = cli_existe

        dados = LancamentoCreate(
            titulo="Custas Processuais",
            tipo=TipoLancamento.SAIDA,
            valor=150.0,
            data_vencimento=datetime.now() + timedelta(days=2),
            categoria_id=categoria_id,
            cliente_id=cliente_id,
        )

        with pytest.raises(ValueError, match=mensagem_esperada):
            lancamento_service.criar_lancamento(dados)

    @pytest.mark.parametrize(
        "dias_vencimento,status_esperado",
        [
            (5, StatusLancamento.PENDENTE),
            (0, StatusLancamento.PENDENTE),
            (-2, StatusLancamento.ATRASADO),
        ],
    )
    def test_criar_lancamento_define_status_automatico(
        self, lancamento_service, dias_vencimento, status_esperado
    ):
        lancamento_service.repository.categoria_existe.return_value = True
        lancamento_service.repository.cliente_existe.return_value = True
        lancamento_service.repository.criar.side_effect = lambda obj: obj

        vencimento = datetime.now() + timedelta(days=dias_vencimento)
        dados = LancamentoCreate(
            titulo="Pagamento Perícia",
            tipo=TipoLancamento.SAIDA,
            valor=500.0,
            data_vencimento=vencimento,
        )

        novo_lancamento = lancamento_service.criar_lancamento(dados)
        assert novo_lancamento.status == status_esperado

    @pytest.mark.parametrize("campo", ["titulo", "tipo", "data_vencimento", "valor"])
    def test_atualizar_lancamento_campo_obrigatorio_nulo_lanca_erro(
        self, lancamento_service, campo
    ):
        lancamento_existente = Lancamento(
            lancamento_id=1,
            titulo="Título Original",
            tipo=TipoLancamento.ENTRADA,
            data_vencimento=datetime.now(),
            valor=100.0,
            status=StatusLancamento.PENDENTE,
        )
        lancamento_service.repository.buscar_por_id.return_value = lancamento_existente

        payload = {campo: None}
        dados_update = LancamentoUpdate(**payload)

        with pytest.raises(ValueError, match=f"O campo '{campo}' não pode ser nulo"):
            lancamento_service.atualizar_lancamento(1, dados_update)

    @pytest.mark.parametrize(
        "status_inicial,dias_novo_vencimento,status_esperado",
        [
            (StatusLancamento.PENDENTE, -5, StatusLancamento.ATRASADO),
            (StatusLancamento.ATRASADO, 5, StatusLancamento.PENDENTE),
            (StatusLancamento.REALIZADO, -5, StatusLancamento.REALIZADO),
        ],
    )
    def test_atualizar_lancamento_data_vencimento_recalcula_status(
        self,
        lancamento_service,
        status_inicial,
        dias_novo_vencimento,
        status_esperado,
    ):
        lancamento_existente = Lancamento(
            lancamento_id=1,
            titulo="Pagamento Fornecedor",
            tipo=TipoLancamento.SAIDA,
            data_vencimento=datetime.now(),
            valor=250.0,
            status=status_inicial,
        )
        lancamento_service.repository.buscar_por_id.return_value = lancamento_existente
        lancamento_service.repository.categoria_existe.return_value = True
        lancamento_service.repository.cliente_existe.return_value = True
        lancamento_service.repository.atualizar.side_effect = lambda obj: obj

        novo_vencimento = datetime.now() + timedelta(days=dias_novo_vencimento)
        dados_update = LancamentoUpdate(data_vencimento=novo_vencimento)

        resultado = lancamento_service.atualizar_lancamento(1, dados_update)

        assert resultado.status == status_esperado
        assert resultado.data_vencimento == novo_vencimento


class TestLancamentoServiceAlternarStatusEDeletar:
    @pytest.mark.parametrize(
        "status_atual,vencimento_dias,status_esperado,tem_data_pagamento",
        [
            (StatusLancamento.PENDENTE, 5, StatusLancamento.REALIZADO, True),
            (StatusLancamento.ATRASADO, -3, StatusLancamento.REALIZADO, True),
            (StatusLancamento.REALIZADO, 5, StatusLancamento.PENDENTE, False),
            (StatusLancamento.REALIZADO, -3, StatusLancamento.ATRASADO, False),
        ],
    )
    def test_alternar_status_transicoes(
        self,
        lancamento_service,
        status_atual,
        vencimento_dias,
        status_esperado,
        tem_data_pagamento,
    ):
        lancamento_mock = Lancamento(
            lancamento_id=1,
            titulo="Diligência",
            status=status_atual,
            data_vencimento=datetime.now() + timedelta(days=vencimento_dias),
            data_pagamento=datetime.now() if status_atual == StatusLancamento.REALIZADO else None,
        )
        lancamento_service.repository.buscar_por_id.return_value = lancamento_mock
        lancamento_service.repository.atualizar.side_effect = lambda obj: obj

        resultado = lancamento_service.alternar_status(1)

        assert resultado.status == status_esperado
        assert (resultado.data_pagamento is not None) == tem_data_pagamento

    def test_deletar_lancamento_sucesso(self, lancamento_service):
        lancamento_mock = Lancamento(lancamento_id=1, titulo="Insumos de Escritório")
        lancamento_service.repository.buscar_por_id.return_value = lancamento_mock

        lancamento_service.deletar_lancamento(1)

        lancamento_service.repository.deletar.assert_called_once_with(lancamento_mock)


class TestLancamentoCalendarioService:
    @pytest.mark.parametrize(
        "inicio,fim,mensagem_esperada",
        [
            (
                None,
                date(2026, 10, 31),
                "As datas inicial e final são obrigatórias para o calendário",
            ),
            (
                date(2026, 10, 1),
                None,
                "As datas inicial e final são obrigatórias para o calendário",
            ),
            (
                date(2026, 10, 31),
                date(2026, 10, 1),
                "A data inicial não pode ser posterior à data final",
            ),
        ],
    )
    def test_obter_calendario_validacao_periodo_invalidos(
        self, calendario_service, inicio, fim, mensagem_esperada
    ):
        filtros = LancamentoFilter(inicio=inicio, fim=fim)
        with pytest.raises(ValueError, match=mensagem_esperada):
            calendario_service.obter_calendario(filtros)

    @pytest.mark.parametrize(
        "tipo,titulo,valor,prefixo_esperado",
        [
            (TipoLancamento.ENTRADA, "Honorários Cíveis", 1500.0, "[Entrada]"),
            (TipoLancamento.SAIDA, "Taxa Judiciária", 300.0, "[Saída]"),
        ],
    )
    def test_obter_calendario_gera_urls_e_prefixos_corretos(
        self, calendario_service, tipo, titulo, valor, prefixo_esperado
    ):
        lancamento_mock = Lancamento(
            lancamento_id=1,
            titulo=titulo,
            tipo=tipo,
            valor=valor,
            data_vencimento=datetime(2026, 10, 25, 14, 0),
            status=StatusLancamento.PENDENTE,
        )
        calendario_service.repositorio.buscar_por_filtros.return_value = [lancamento_mock]

        filtros = LancamentoFilter(inicio=date(2026, 10, 1), fim=date(2026, 10, 31))
        resultado = calendario_service.obter_calendario(filtros)

        assert len(resultado) == 1
        item = resultado[0]
        assert isinstance(item, LancamentoCalendarioResponse)
        assert item.titulo == titulo
        assert "calendar.google.com" in item.google_calendar_url
        assert "outlook.office.com" in item.outlook_calendar_url

    def test_exportar_icalendar_gera_conteudo_ics_valido(self, calendario_service):
        lancamento_mock = Lancamento(
            lancamento_id=1,
            titulo="Aluguel do Escritório",
            tipo=TipoLancamento.SAIDA,
            valor=2500.0,
            data_vencimento=datetime(2026, 10, 30, 9, 0),
            status=StatusLancamento.PENDENTE,
            descricao="Aluguel referente ao mês de Outubro",
        )
        calendario_service.repositorio.buscar_por_filtros.return_value = [lancamento_mock]

        filtros = LancamentoFilter(inicio=date(2026, 10, 1), fim=date(2026, 10, 31))
        ics_conteudo = calendario_service.exportar_icalendar(filtros)

        assert "BEGIN:VCALENDAR" in ics_conteudo
        assert "END:VCALENDAR" in ics_conteudo
        assert "BEGIN:VEVENT" in ics_conteudo
        assert "SUMMARY:[Saída] Aluguel do Escritório - R$ 2500.00" in ics_conteudo

    def test_exportar_icalendar_lancamento_sem_descricao(self, calendario_service):
        lancamento_mock = Lancamento(
            lancamento_id=1,
            titulo="Consulta Simples",
            tipo=TipoLancamento.ENTRADA,
            valor=300.0,
            data_vencimento=datetime(2026, 10, 25, 10, 0),
            status=StatusLancamento.PENDENTE,
            descricao=None,
        )
        calendario_service.repositorio.buscar_por_filtros.return_value = [lancamento_mock]

        filtros = LancamentoFilter(inicio=date(2026, 10, 1), fim=date(2026, 10, 31))
        ical_output = calendario_service.exportar_icalendar(filtros)

        assert "BEGIN:VCALENDAR" in ical_output
        assert "UID:lancamento-1@escritorio.com.br" in ical_output
        assert "SUMMARY:[Entrada] Consulta Simples - R$ 300.00" in ical_output

    def test_inicializacao_calendario_service_com_session(self):
        class MockSession(Session):
            def __init__(self):
                pass

        mock_session = MockSession()
        service = LancamentoCalendarioService(mock_session)
        assert isinstance(service.repositorio, LancamentoRepository)
