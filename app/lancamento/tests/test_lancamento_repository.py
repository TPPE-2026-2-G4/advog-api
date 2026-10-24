from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.categoria_lancamento.model import CategoriaLancamento
from app.cliente.model import Cliente
from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento
from app.lancamento.repository import LancamentoRepository


@pytest.fixture
def categoria_bd(db_session: Session) -> CategoriaLancamento:
    categoria = CategoriaLancamento(nome_categoria="Honorários Repositório")
    db_session.add(categoria)
    db_session.commit()
    db_session.refresh(categoria)
    return categoria


@pytest.fixture
def cliente_bd(db_session: Session) -> Cliente:
    cliente = Cliente(nome="Cliente Teste Repositório", email="cliente_repo@teste.com")
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


class TestLancamentoRepositoryOperacoesBasicas:
    def test_criar_e_buscar_por_id(self, db_session: Session):
        repo = LancamentoRepository(db_session)
        novo = Lancamento(
            titulo="Consulta Inicial",
            tipo=TipoLancamento.ENTRADA,
            valor=500.0,
            data_vencimento=datetime.now(),
            status=StatusLancamento.PENDENTE,
        )

        criado = repo.criar(novo)
        assert criado.lancamento_id is not None

        buscado = repo.buscar_por_id(criado.lancamento_id)
        assert buscado is not None
        assert buscado.titulo == "Consulta Inicial"

    def test_atualizar_e_deletar(self, db_session: Session):
        repo = LancamentoRepository(db_session)
        lancamento = Lancamento(
            titulo="Taxa Cartório",
            tipo=TipoLancamento.SAIDA,
            valor=100.0,
            data_vencimento=datetime.now(),
            status=StatusLancamento.PENDENTE,
        )
        repo.criar(lancamento)

        lancamento.titulo = "Taxa Cartório Alterada"
        atualizado = repo.atualizar(lancamento)
        assert atualizado.titulo == "Taxa Cartório Alterada"

        repo.deletar(atualizado)
        assert repo.buscar_por_id(lancamento.lancamento_id) is None

    @pytest.mark.parametrize(
        "metodo_checagem,id_valido,id_invalido",
        [
            ("categoria_existe", "categoria_bd", 999999),
            ("cliente_existe", "cliente_bd", 999999),
        ],
    )
    def test_verificar_existencia_referencias(
        self,
        db_session: Session,
        categoria_bd: CategoriaLancamento,
        cliente_bd: Cliente,
        metodo_checagem: str,
        id_valido: str,
        id_invalido: int,
    ):
        repo = LancamentoRepository(db_session)
        id_real = (
            categoria_bd.categoria_id if id_valido == "categoria_bd" else cliente_bd.cliente_id
        )
        metodo = getattr(repo, metodo_checagem)

        assert metodo(id_real) is True
        assert metodo(id_invalido) is False

    @pytest.mark.parametrize(
        "dias_vencimento,status_inicial,status_esperado",
        [
            (-2, StatusLancamento.PENDENTE, StatusLancamento.ATRASADO),
            (2, StatusLancamento.PENDENTE, StatusLancamento.PENDENTE),
            (-2, StatusLancamento.REALIZADO, StatusLancamento.REALIZADO),
        ],
    )
    def test_marcar_atrasados_com_diferentes_cenarios(
        self,
        db_session: Session,
        dias_vencimento: int,
        status_inicial: StatusLancamento,
        status_esperado: StatusLancamento,
    ):
        repo = LancamentoRepository(db_session)
        hoje = date.today()
        vencimento = datetime.combine(hoje + timedelta(days=dias_vencimento), datetime.min.time())

        lancamento = Lancamento(
            titulo="Lançamento Teste Atraso",
            tipo=TipoLancamento.SAIDA,
            valor=150.0,
            data_vencimento=vencimento,
            status=status_inicial,
        )
        repo.criar(lancamento)

        repo.marcar_atrasados(hoje)

        buscado = repo.buscar_por_id(lancamento.lancamento_id)
        assert buscado is not None
        assert buscado.status == status_esperado

    def test_pendente_vencido_vira_atrasado_automaticamente(self, db_session: Session):
        repo = LancamentoRepository(db_session)
        hoje = date.today()
        lancamento = Lancamento(
            titulo="Antigo",
            tipo=TipoLancamento.SAIDA,
            valor=10.0,
            status=StatusLancamento.PENDENTE,
            data_vencimento=datetime.now() - timedelta(days=2),
        )
        repo.criar(lancamento)
        repo.marcar_atrasados(hoje)

        buscado = repo.buscar_por_id(lancamento.lancamento_id)
        assert buscado is not None
        assert buscado.status == StatusLancamento.ATRASADO


class TestLancamentoRepositoryFiltrosEConsultas:
    @pytest.mark.parametrize(
        "campo_filtro,obter_valor,quantidade_esperada",
        [
            ("status", lambda cat_id, cli_id: StatusLancamento.PENDENTE, 1),
            ("tipo", lambda cat_id, cli_id: TipoLancamento.ENTRADA, 1),
            ("categoria_id", lambda cat_id, cli_id: cat_id, 1),
            ("cliente_id", lambda cat_id, cli_id: cli_id, 1),
        ],
    )
    def test_buscar_por_filtros_isolados(
        self,
        db_session: Session,
        categoria_bd: CategoriaLancamento,
        cliente_bd: Cliente,
        campo_filtro: str,
        obter_valor,
        quantidade_esperada: int,
    ):
        repo = LancamentoRepository(db_session)
        hoje = date.today()

        item_alvo = Lancamento(
            titulo="Honorário Específico",
            tipo=TipoLancamento.ENTRADA,
            valor=1500.0,
            data_vencimento=datetime.combine(hoje, datetime.min.time()),
            status=StatusLancamento.PENDENTE,
            categoria_id=categoria_bd.categoria_id,
            cliente_id=cliente_bd.cliente_id,
        )
        repo.criar(item_alvo)

        valor_filtro = obter_valor(categoria_bd.categoria_id, cliente_bd.cliente_id)
        filtros = {
            "inicio": None,
            "fim": None,
            "status": None,
            "tipo": None,
            "categoria_id": None,
            "cliente_id": None,
            campo_filtro: valor_filtro,
        }
        resultados = repo.buscar_por_filtros(**filtros)

        assert len(resultados) == quantidade_esperada
        assert resultados[0].lancamento_id == item_alvo.lancamento_id

    def test_buscar_por_filtros_e_paginado_com_filtros_combinados(
        self, db_session: Session, categoria_bd: CategoriaLancamento, cliente_bd: Cliente
    ):
        repo = LancamentoRepository(db_session)
        hoje = date.today()

        item_alvo = Lancamento(
            titulo="Honorário Específico",
            tipo=TipoLancamento.ENTRADA,
            valor=1500.0,
            data_vencimento=datetime.combine(hoje, datetime.min.time()),
            status=StatusLancamento.PENDENTE,
            categoria_id=categoria_bd.categoria_id,
            cliente_id=cliente_bd.cliente_id,
        )
        item_outros = Lancamento(
            titulo="Despesa Geral",
            tipo=TipoLancamento.SAIDA,
            valor=300.0,
            data_vencimento=datetime.combine(hoje + timedelta(days=5), datetime.min.time()),
            status=StatusLancamento.REALIZADO,
        )
        repo.criar(item_alvo)
        repo.criar(item_outros)

        filtros = {
            "inicio": hoje - timedelta(days=1),
            "fim": hoje + timedelta(days=1),
            "status": StatusLancamento.PENDENTE,
            "tipo": TipoLancamento.ENTRADA,
            "categoria_id": categoria_bd.categoria_id,
            "cliente_id": cliente_bd.cliente_id,
        }

        resultados_filtros = repo.buscar_por_filtros(**filtros)
        assert len(resultados_filtros) == 1
        assert resultados_filtros[0].titulo == "Honorário Específico"

        itens_paginados, total = repo.buscar_paginado(page=1, page_size=10, **filtros)
        assert total == 1
        assert len(itens_paginados) == 1
        assert itens_paginados[0].lancamento_id == item_alvo.lancamento_id

    def test_totais_por_status_e_tipo(self, db_session: Session):
        repo = LancamentoRepository(db_session)
        l1 = Lancamento(
            titulo="Entrada 1",
            tipo=TipoLancamento.ENTRADA,
            valor=500.0,
            data_vencimento=datetime.now(),
            status=StatusLancamento.PENDENTE,
        )
        l2 = Lancamento(
            titulo="Saída 1",
            tipo=TipoLancamento.SAIDA,
            valor=200.0,
            data_vencimento=datetime.now(),
            status=StatusLancamento.PENDENTE,
        )
        repo.criar(l1)
        repo.criar(l2)

        totais = repo.totais_por_status_e_tipo(
            inicio=None, fim=None, status=None, tipo=None, categoria_id=None, cliente_id=None
        )

        assert len(totais) >= 2

    def test_buscar_por_filtros_com_valor_min_e_valor_max(self, db_session):
        repo = LancamentoRepository(db_session)
        resultados = repo.buscar_por_filtros(
            valor_min=100.0,
            valor_max=500.0,
        )
        assert isinstance(resultados, list)

    def test_totais_por_dia_e_tipo_com_filtros_de_valor(self, db_session):
        repo = LancamentoRepository(db_session)
        resultados = repo.totais_por_dia_e_tipo(
            valor_min=50.0,
            valor_max=1000.0,
        )
        assert isinstance(resultados, list)
