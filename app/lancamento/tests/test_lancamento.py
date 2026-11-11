import io
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.categoria_lancamento.model import CategoriaLancamento
from app.cliente.model import Cliente
from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento
from app.lancamento.repository import LancamentoRepository
from app.lancamento.schema import (
    LancamentoCalendarioResponse,
    LancamentoCreate,
    LancamentoFilter,
    LancamentoUpdate,
)
from app.lancamento.service import (
    LancamentoCalendarioService,
    LancamentoService,
    datas_recorrentes,
    reancorar_regra,
)


@pytest.fixture()
def client_controller(client: TestClient, token_admin: str) -> TestClient:
    client.headers["Authorization"] = f"Bearer {token_admin}"
    client.post("/categorias-lancamento", json={"nome_categoria": "Categoria Padrão"})
    return client


def _payload_lancamento(**kwargs) -> dict:
    base = {
        "titulo": "Honorários Advocatícios",
        "descricao": "Honorários do mês",
        "categoria_id": 1,  # categoria criada pela fixture client_controller
        "tipo": "e",
        "valor": 1200.0,
        "data_vencimento": (datetime.now() + timedelta(days=5)).isoformat(),
    }
    return {**base, **kwargs}


def _dias(n: int) -> str:
    return (datetime.now() + timedelta(days=n)).isoformat()


def _popular(client_controller: TestClient) -> None:
    client_controller.post("/lancamentos/", json=_payload_lancamento(titulo="pendente", valor=100))
    feito = client_controller.post(
        "/lancamentos/",
        json=_payload_lancamento(titulo="feito", tipo="s", valor=50, data_vencimento=_dias(-10)),
    ).json()
    client_controller.patch(f"/lancamentos/{feito['lancamento_id']}/alternar-status")
    client_controller.post(
        "/lancamentos/",
        json=_payload_lancamento(titulo="atrasado", valor=200, data_vencimento=_dias(-3)),
    )


class TestLancamentoControllerCRUD:
    def test_criar_e_buscar_lancamento(self, client_controller: TestClient):
        response_criar = client_controller.post("/lancamentos/", json=_payload_lancamento())
        assert response_criar.status_code == 201
        dados_criados = response_criar.json()
        assert dados_criados["titulo"] == "Honorários Advocatícios"

        lid = dados_criados["lancamento_id"]
        response_listar = client_controller.get("/lancamentos/")
        assert response_listar.status_code == 200
        assert any(item["lancamento_id"] == lid for item in response_listar.json())

    def test_criar_lancamento_com_categoria(self, client_controller: TestClient):
        cat = client_controller.post(
            "/categorias-lancamento", json={"nome_categoria": "Honorários"}
        ).json()
        payload = _payload_lancamento(categoria_id=cat["categoria_id"])
        response = client_controller.post("/lancamentos/", json=payload)
        assert response.status_code == 201
        dados = response.json()
        assert dados["status"] == "Pendente"
        assert dados["data_pagamento"] is None
        assert dados["categoria_id"] == cat["categoria_id"]

    @pytest.mark.parametrize("campo", ["descricao", "categoria_id"])
    def test_criar_lancamento_sem_campo_obrigatorio_retorna_422(
        self, client_controller: TestClient, campo
    ):
        payload = _payload_lancamento()
        del payload[campo]
        assert client_controller.post("/lancamentos/", json=payload).status_code == 422

    def test_criar_lancamento_tipo_invalido(self, client_controller: TestClient):
        response = client_controller.post("/lancamentos/", json=_payload_lancamento(tipo="x"))
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "payload_extra,status_esperado,mensagem_erro",
        [
            ({"categoria_id": 999999}, 404, "Categoria não encontrada"),
            ({"cliente_id": 999999}, 404, "Cliente não encontrado"),
        ],
    )
    def test_criar_lancamento_com_referencias_invalidas_retorna_404(
        self,
        client_controller: TestClient,
        payload_extra: dict,
        status_esperado: int,
        mensagem_erro: str,
    ):
        payload = _payload_lancamento(**payload_extra)
        response = client_controller.post("/lancamentos/", json=payload)

        assert response.status_code == status_esperado
        assert response.json()["detail"] == mensagem_erro

    @pytest.mark.parametrize(
        "metodo,endpoint,json_body",
        [
            ("put", "/lancamentos/999999", {"titulo": "Teste Inexistente"}),
            ("patch", "/lancamentos/999999/alternar-status", None),
            ("delete", "/lancamentos/999999", None),
        ],
    )
    def test_operacoes_com_id_inexistente_retornam_404(
        self, client_controller: TestClient, metodo: str, endpoint: str, json_body: dict | None
    ):
        funcao_http = getattr(client_controller, metodo)
        kwargs = {"json": json_body} if json_body else {}
        response = funcao_http(endpoint, **kwargs)

        assert response.status_code == 404
        assert response.json()["detail"] == "Lançamento não encontrado"

    def test_atualizar_lancamento_sucesso_e_campo_nulo_retorna_400(
        self, client_controller: TestClient
    ):
        lid = client_controller.post("/lancamentos/", json=_payload_lancamento()).json()[
            "lancamento_id"
        ]

        response_atualizar = client_controller.put(
            f"/lancamentos/{lid}", json={"titulo": "Honorários Revisados"}
        )
        assert response_atualizar.status_code == 200
        assert response_atualizar.json()["titulo"] == "Honorários Revisados"

        response_nulo = client_controller.put(f"/lancamentos/{lid}", json={"titulo": None})
        assert response_nulo.status_code == 400

    @pytest.mark.parametrize("campo", ["descricao", "categoria_id"])
    def test_atualizar_lancamento_campo_obrigatorio_nulo_retorna_400(
        self, client_controller: TestClient, campo: str
    ):
        lid = client_controller.post("/lancamentos/", json=_payload_lancamento()).json()[
            "lancamento_id"
        ]

        response = client_controller.put(f"/lancamentos/{lid}", json={campo: None})

        assert response.status_code == 400
        assert response.json()["detail"] == f"O campo '{campo}' não pode ser nulo"

    def test_alternar_status_sucesso(self, client_controller: TestClient):
        lid = client_controller.post("/lancamentos/", json=_payload_lancamento()).json()[
            "lancamento_id"
        ]

        response_alternar = client_controller.patch(f"/lancamentos/{lid}/alternar-status")
        assert response_alternar.status_code == 200
        assert response_alternar.json()["status"] == "Realizado"

    def test_rota_de_status_manual_removida(self, client_controller: TestClient):
        lid = client_controller.post("/lancamentos/", json=_payload_lancamento()).json()[
            "lancamento_id"
        ]
        response = client_controller.patch(
            f"/lancamentos/{lid}/status", json={"status": "Realizado"}
        )
        assert response.status_code in (404, 405)

    def test_remover_lancamento_sucesso(self, client_controller: TestClient):
        lid = client_controller.post("/lancamentos/", json=_payload_lancamento()).json()[
            "lancamento_id"
        ]

        response_deletar = client_controller.delete(f"/lancamentos/{lid}")
        assert response_deletar.status_code == 204
        assert client_controller.delete(f"/lancamentos/{lid}").status_code == 404


class TestLancamentoControllerConsultasEResumo:
    def test_filtrar_por_status(self, client_controller: TestClient):
        _popular(client_controller)
        for status, titulo in [
            ("Pendente", "pendente"),
            ("Realizado", "feito"),
            ("Atrasado", "atrasado"),
        ]:
            response = client_controller.get("/lancamentos/", params={"status": status})
            assert response.status_code == 200
            assert [item["titulo"] for item in response.json()] == [titulo]

    def test_filtrar_por_periodo(self, client_controller: TestClient):
        _popular(client_controller)
        hoje = datetime.now().date()
        response = client_controller.get(
            "/lancamentos/",
            params={"inicio": (hoje - timedelta(days=5)).isoformat(), "fim": hoje.isoformat()},
        )
        assert response.status_code == 200
        assert [item["titulo"] for item in response.json()] == ["atrasado"]

    @pytest.mark.parametrize(
        "endpoint,params",
        [
            ("/lancamentos/", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
            ("/lancamentos/paginado", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
            ("/lancamentos/resumo", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
            ("/lancamentos/grafico", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
            ("/lancamentos/grafico", {"valor_min": 500.0, "valor_max": 100.0}),
            ("/lancamentos/calendario", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
            ("/lancamentos/calendario/exportar", {"inicio": "2026-10-10", "fim": "2026-10-01"}),
        ],
    )
    def test_endpoints_com_periodo_invalido_retornam_400(
        self, client_controller: TestClient, endpoint: str, params: dict
    ):
        response = client_controller.get(endpoint, params=params)
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "params",
        [
            {"dias": 0},
            {"dias": -3},
            {"valor_min": -1.0},
            {"valor_max": -0.01},
        ],
    )
    def test_grafico_parametros_invalidos_retornam_422(
        self, client_controller: TestClient, params: dict
    ):
        response = client_controller.get("/lancamentos/grafico", params=params)
        assert response.status_code == 422

    def test_listar_paginado_sucesso(self, client_controller: TestClient):
        _popular(client_controller)
        response_paginado = client_controller.get(
            "/lancamentos/paginado", params={"page": 1, "page_size": 2}
        )
        assert response_paginado.status_code == 200
        data = response_paginado.json()
        assert data["total"] == 3 and data["total_pages"] == 2
        assert [item["titulo"] for item in data["itens"]] == ["feito", "atrasado"]

        data_p2 = client_controller.get(
            "/lancamentos/paginado", params={"page": 2, "page_size": 2}
        ).json()
        assert [item["titulo"] for item in data_p2["itens"]] == ["pendente"]

    def test_listar_paginado_com_filtros(self, client_controller: TestClient):
        _popular(client_controller)
        data = client_controller.get("/lancamentos/paginado", params={"status": "Atrasado"}).json()
        assert data["total"] == 1 and data["itens"][0]["titulo"] == "atrasado"
        vazio = client_controller.get(
            "/lancamentos/paginado", params={"tipo": "s", "status": "Pendente"}
        ).json()
        assert vazio == {"itens": [], "total": 0, "page": 1, "page_size": 10, "total_pages": 1}

    def test_listar_paginado_validacoes(self, client_controller: TestClient):
        assert client_controller.get("/lancamentos/paginado", params={"page": 0}).status_code == 422
        assert (
            client_controller.get("/lancamentos/paginado", params={"page_size": 101}).status_code
            == 422
        )
        r = client_controller.get(
            "/lancamentos/paginado", params={"inicio": "2026-10-10", "fim": "2026-10-01"}
        )
        assert r.status_code == 400

    def test_resumir_lancamentos_sucesso(self, client_controller: TestClient):
        client_controller.post("/lancamentos/", json=_payload_lancamento())

        response_resumo = client_controller.get("/lancamentos/resumo")
        assert response_resumo.status_code == 200
        data = response_resumo.json()
        assert "pendente" in data

    def test_obter_grafico_sucesso(self, client_controller: TestClient):
        _popular(client_controller)
        response = client_controller.get("/lancamentos/grafico")
        assert response.status_code == 200
        data = response.json()
        assert "total_entradas" in data or "itens" in data


class TestCalendarioLancamentoController:
    @pytest.mark.parametrize(
        "params,status_code_esperado",
        [
            ({}, 400),
            ({"inicio": "2026-10-01", "fim": "2026-10-31"}, 200),
            ({"inicio": "2026-10-31", "fim": "2026-10-01"}, 400),
        ],
    )
    def test_obter_calendario_validacoes(
        self, client_controller: TestClient, params: dict, status_code_esperado: int
    ):
        response = client_controller.get("/lancamentos/calendario", params=params)
        assert response.status_code == status_code_esperado

    def test_exportar_icalendar_sucesso_headers(self, client_controller: TestClient):
        client_controller.post("/lancamentos/", json=_payload_lancamento(titulo="Atendimento 1"))

        params_ok = {"inicio": "2026-10-01", "fim": "2026-10-31"}
        response = client_controller.get("/lancamentos/calendario/exportar", params=params_ok)

        assert response.status_code == 200
        assert "text/calendar" in response.headers["content-type"]
        assert (
            'attachment; filename="calendario_financeiro.ics"'
            in response.headers["content-disposition"]
        )
        assert "BEGIN:VCALENDAR" in response.text


class TestLancamentoAutenticacao:
    @pytest.mark.parametrize(
        "metodo,endpoint,json_body",
        [
            ("get", "/lancamentos/", None),
            ("get", "/lancamentos/resumo", None),
            ("get", "/lancamentos/grafico", None),
            ("get", "/lancamentos/paginado", None),
            ("get", "/lancamentos/calendario", None),
            ("get", "/lancamentos/calendario/exportar", None),
            ("post", "/lancamentos/", _payload_lancamento()),
            ("put", "/lancamentos/1", {}),
            ("patch", "/lancamentos/1/alternar-status", None),
            ("delete", "/lancamentos/1", None),
        ],
    )
    def test_rotas_exigem_autenticacao(
        self, client: TestClient, metodo: str, endpoint: str, json_body: dict | None
    ):
        client.headers.pop("Authorization", None)
        funcao_http = getattr(client, metodo)
        kwargs = {"json": json_body} if json_body else {}
        response = funcao_http(endpoint, **kwargs)

        assert response.status_code == 401


ROTA = "/lancamentos/exportar"


@pytest.fixture
def auth(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture
def lancamentos(db_session):
    categoria = CategoriaLancamento(nome_categoria="Honorários")
    cliente = Cliente(nome="Maria da Silva", email="maria@teste.com", telefone="61999999999")
    db_session.add_all([categoria, cliente])
    db_session.flush()
    itens = [
        Lancamento(
            descricao="Descrição",
            titulo="Honorário A",
            tipo=TipoLancamento.ENTRADA,
            status=StatusLancamento.REALIZADO,
            data_vencimento=datetime(2099, 1, 10),
            data_pagamento=datetime(2099, 1, 9),
            valor=1000.0,
            categoria_id=categoria.categoria_id,
            cliente_id=cliente.cliente_id,
        ),
        Lancamento(
            descricao="Descrição",
            categoria_id=1,
            titulo="Aluguel",
            tipo=TipoLancamento.SAIDA,
            status=StatusLancamento.PENDENTE,
            data_vencimento=datetime(2099, 1, 20),
            valor=400.5,
        ),
    ]
    db_session.add_all(itens)
    db_session.commit()
    return itens


def _planilha(response):
    return load_workbook(io.BytesIO(response.content)).active


@pytest.mark.parametrize(
    ("formato", "inicio"), [("csv", b"\xef\xbb\xbf"), ("xlsx", b"PK"), ("pdf", b"%PDF")]
)
def test_exportacao_exportar_cada_formato(client, auth, lancamentos, formato, inicio):
    response = client.get(ROTA, params={"formato": formato}, headers=auth)

    assert response.status_code == 200
    assert response.content.startswith(inicio)
    assert "lancamentos_" in response.headers["content-disposition"]


def test_exportacao_exportar_conteudo_e_totais(client, auth, lancamentos):
    planilha = _planilha(client.get(ROTA, params={"formato": "xlsx"}, headers=auth))

    cabecalho = [c.value for c in planilha[1]]
    linha = {nome: planilha.cell(2, i + 1).value for i, nome in enumerate(cabecalho)}
    assert linha["Título"] == "Honorário A"
    assert linha["Tipo"] == "Entrada"
    assert linha["Status"] == "Realizado"
    assert linha["Categoria"] == "Honorários"
    assert linha["Cliente"] == "Maria da Silva"
    assert linha["Valor"] == 1000.0
    assert planilha.cell(3, cabecalho.index("Tipo") + 1).value == "Saída"
    totais = {
        planilha.cell(i, 1).value: planilha.cell(i, 2).value for i in range(5, planilha.max_row + 1)
    }
    assert totais == {
        "Total de entradas": 1000.0,
        "Total de saídas": 400.5,
        "Saldo": 599.5,
    }


def test_exportacao_exportar_aplica_filtros_da_listagem(client, auth, lancamentos):
    planilha = _planilha(
        client.get(ROTA, params={"formato": "xlsx", "tipo": "s", "valor_min": 100}, headers=auth)
    )

    assert planilha.cell(2, 1).value == "Aluguel"
    assert planilha.cell(3, 1).value is None
    assert planilha.cell(4, 2).value == 0.0  # total de entradas do conjunto filtrado
    assert planilha.cell(5, 2).value == 400.5


@pytest.mark.parametrize(
    "filtros",
    [{"inicio": "2099-02-01", "fim": "2099-01-01"}, {"valor_min": 10, "valor_max": 5}],
)
def test_exportacao_exportar_filtros_invalidos(client, auth, filtros):
    response = client.get(ROTA, params={"formato": "csv", **filtros}, headers=auth)

    assert response.status_code == 422


def test_exportacao_exportar_respeita_limite_de_linhas(client, auth, lancamentos, monkeypatch):
    monkeypatch.setattr("app.lancamento.service.LIMITE_LINHAS", 1)

    response = client.get(ROTA, params={"formato": "csv"}, headers=auth)

    assert response.status_code == 422
    assert "refine os filtros" in response.json()["detail"]


def test_exportacao_exportar_exige_visualizar_financeiro(
    client, token_acesso, funcionario_sem_permissao
):
    usuario = funcionario_sem_permissao
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get(
        ROTA, params={"formato": "csv"}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "rota",
    [
        "/lancamentos/",
        "/lancamentos/paginado",
        "/lancamentos/resumo",
        "/lancamentos/grafico",
        "/lancamentos/calendario",
        "/lancamentos/calendario/exportar",
    ],
)
def test_consultas_financeiras_exigem_visualizar_financeiro(
    client, db_session, token_acesso, funcionario_sem_permissao, rota
):
    usuario = funcionario_sem_permissao
    headers = {"Authorization": f"Bearer {token_acesso(usuario.funcionario_id, usuario.email)}"}

    assert client.get(rota, headers=headers).status_code == 403

    usuario.cargo.permissao = {"visualizar_financeiro": True}
    db_session.commit()

    assert client.get(rota, headers=headers).status_code != 403


def test_gerenciar_financeiro_inclui_visualizacao(
    client, db_session, token_acesso, funcionario_sem_permissao
):
    usuario = funcionario_sem_permissao
    usuario.cargo.permissao = {"gerenciar_financeiro": True}
    db_session.commit()
    headers = {"Authorization": f"Bearer {token_acesso(usuario.funcionario_id, usuario.email)}"}

    assert client.get("/lancamentos/", headers=headers).status_code == 200


@pytest.mark.parametrize(
    ("metodo", "rota", "corpo", "permitido"),
    [
        ("post", "/lancamentos/", {}, 422),
        ("put", "/lancamentos/1", {}, 404),
        ("patch", "/lancamentos/1/alternar-status", None, 404),
        ("delete", "/lancamentos/1", None, 404),
        ("post", "/categorias-lancamento", {}, 422),
        ("put", "/categorias-lancamento/1", {"nome_categoria": "Nova"}, 404),
        ("delete", "/categorias-lancamento/1", None, 404),
    ],
)
def test_escritas_financeiras_exigem_gerenciar_financeiro(
    client, db_session, token_acesso, funcionario_sem_permissao, metodo, rota, corpo, permitido
):
    usuario = funcionario_sem_permissao
    headers = {"Authorization": f"Bearer {token_acesso(usuario.funcionario_id, usuario.email)}"}

    for permissao in ({"visualizar_financeiro": True}, {"gerenciar_financeiro": True}):
        usuario.cargo.permissao = permissao
        db_session.commit()
        resposta = client.request(metodo, rota, json=corpo, headers=headers)
        assert resposta.status_code == (permitido if "gerenciar_financeiro" in permissao else 403)


def test_exportacao_exportar_exige_autenticacao(client):
    assert client.get(ROTA, params={"formato": "csv"}).status_code == 401


@pytest.fixture
def categoria_bd(db_session: Session) -> CategoriaLancamento:
    categoria = CategoriaLancamento(nome_categoria="Honorários Repositório")
    db_session.add(categoria)
    db_session.commit()
    db_session.refresh(categoria)
    return categoria


@pytest.fixture
def cliente_bd(db_session: Session) -> Cliente:
    cliente = Cliente(
        nome="Cliente Teste Repositório",
        email="cliente_repo@teste.com",
        telefone="61999999999",
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


class TestLancamentoRepositoryOperacoesBasicas:
    def test_criar_e_buscar_por_id(self, db_session: Session):
        repo = LancamentoRepository(db_session)
        novo = Lancamento(
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
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
            descricao="Descrição",
            titulo="Honorário Específico",
            tipo=TipoLancamento.ENTRADA,
            valor=1500.0,
            data_vencimento=datetime.combine(hoje, datetime.min.time()),
            status=StatusLancamento.PENDENTE,
            categoria_id=categoria_bd.categoria_id,
            cliente_id=cliente_bd.cliente_id,
        )
        item_outros = Lancamento(
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
            categoria_id=1,
            titulo="Entrada 1",
            tipo=TipoLancamento.ENTRADA,
            valor=500.0,
            data_vencimento=datetime.now(),
            status=StatusLancamento.PENDENTE,
        )
        l2 = Lancamento(
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
            categoria_id=1,
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
            (1, 88, True, False, "Cliente não encontrado"),
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
            descricao="Custas",
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
            descricao="Perícia",
            tipo=TipoLancamento.SAIDA,
            valor=500.0,
            data_vencimento=vencimento,
            categoria_id=1,
        )

        novo_lancamento = lancamento_service.criar_lancamento(dados)
        assert novo_lancamento.status == status_esperado

    @pytest.mark.parametrize(
        "campo", ["titulo", "descricao", "tipo", "data_vencimento", "valor", "categoria_id"]
    )
    def test_atualizar_lancamento_campo_obrigatorio_nulo_lanca_erro(
        self, lancamento_service, campo
    ):
        lancamento_existente = Lancamento(
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
            categoria_id=1,
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
            descricao="Descrição",
            categoria_id=1,
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
        lancamento_mock = Lancamento(
            descricao="Descrição", categoria_id=1, lancamento_id=1, titulo="Insumos de Escritório"
        )
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
            descricao="Descrição",
            categoria_id=1,
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
            categoria_id=1,
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
            categoria_id=1,
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


def _criar_serie(client_controller: TestClient, **campos) -> list[dict]:
    response = client_controller.post(
        "/lancamentos/",
        json=_payload_lancamento(
            titulo="Honorários",
            descricao="Assessoria mensal",
            valor=100,
            tipo="e",
            data_vencimento="2027-01-04T00:00:00",
            rrule="FREQ=WEEKLY;BYDAY=MO;COUNT=5",
            **campos,
        ),
    )
    assert response.status_code == 201, response.text
    return client_controller.get("/lancamentos/").json()


class TestLancamentoControllerRecorrencia:
    def test_cadastro_listagem_calendario_resumo(self, client_controller: TestClient):
        itens = _criar_serie(client_controller)
        assert len(itens) == 5
        assert len({i["serie_id"] for i in itens}) == 1
        assert itens[0]["serie_id"] is not None
        assert all(i["data_pagamento"] is None for i in itens)
        assert client_controller.get("/lancamentos/paginado?page_size=2").json()["total"] == 5
        eventos = client_controller.get(
            "/lancamentos/calendario?inicio=2027-01-01&fim=2027-01-31"
        ).json()
        assert len(eventos) == 4
        assert eventos[0]["serie_id"] == itens[0]["serie_id"]
        resumo = client_controller.get("/lancamentos/resumo").json()
        assert resumo["pendente"]["total_entradas"] == 500

    def test_editar_serie_preserva_anteriores_realizados_e_ids(self, client_controller: TestClient):
        itens = _criar_serie(client_controller)
        pago = itens[2]["lancamento_id"]
        client_controller.patch(f"/lancamentos/{pago}/alternar-status")
        alvo = itens[1]["lancamento_id"]
        response = client_controller.put(
            f"/lancamentos/{alvo}?alcance=serie",
            json={
                "titulo": "Novo título",
                "descricao": "Nova descrição",
                "valor": 200,
                "tipo": "s",
                "data_vencimento": "2027-01-13T00:00:00",
            },
        )
        assert response.status_code == 200, response.text
        atualizados = {i["lancamento_id"]: i for i in client_controller.get("/lancamentos/").json()}
        assert set(atualizados) == {i["lancamento_id"] for i in itens}
        assert atualizados[itens[0]["lancamento_id"]] == itens[0]
        assert atualizados[pago]["status"] == "Realizado"
        assert atualizados[pago]["data_vencimento"] == itens[2]["data_vencimento"]
        assert atualizados[pago]["valor"] == 100
        assert atualizados[itens[3]["lancamento_id"]]["data_vencimento"].startswith("2027-01-27")
        assert atualizados[alvo]["valor"] == 200
        assert atualizados[alvo]["tipo"] == "s"

    def test_edicao_individual_e_exclusao_serie(self, client_controller: TestClient):
        itens = _criar_serie(client_controller)
        alvo = itens[1]["lancamento_id"]
        client_controller.put(f"/lancamentos/{alvo}", json={"valor": 250})
        assert [i["valor"] for i in client_controller.get("/lancamentos/").json()] == [
            100,
            250,
            100,
            100,
            100,
        ]
        pago = itens[3]["lancamento_id"]
        client_controller.patch(f"/lancamentos/{pago}/alternar-status")
        assert client_controller.delete(f"/lancamentos/{alvo}?alcance=serie").status_code == 204
        restantes = client_controller.get("/lancamentos/").json()
        assert {i["lancamento_id"] for i in restantes} == {itens[0]["lancamento_id"], pago}

    def test_exclusao_individual_nao_apaga_serie(self, client_controller: TestClient):
        itens = _criar_serie(client_controller)
        assert (
            client_controller.delete(f"/lancamentos/{itens[1]['lancamento_id']}").status_code == 204
        )
        assert len(client_controller.get("/lancamentos/").json()) == 4

    def test_regra_invalida_nao_persiste_parcialmente(self, client_controller: TestClient):
        response = client_controller.post(
            "/lancamentos/",
            json=_payload_lancamento(
                titulo="Inválido",
                descricao="Sem persistência",
                valor=100,
                tipo="e",
                data_vencimento="2027-01-01",
                rrule="FREQ=DAILY;INTERVAL=0",
            ),
        )
        assert response.status_code == 400
        assert client_controller.get("/lancamentos/").json() == []


class TestLancamentoServiceRecorrencia:
    @pytest.mark.parametrize("operacao", ["criar", "editar", "excluir"])
    def test_rollback_serie(self, operacao: str):
        db = MagicMock()
        db.commit.side_effect = RuntimeError("Falha ao persistir")
        repository = LancamentoRepository(db)
        itens = [Lancamento(status=StatusLancamento.PENDENTE)]
        with pytest.raises(RuntimeError):
            if operacao == "criar":
                repository.criar_serie(itens)
            else:
                repository.salvar_serie(itens, excluir=operacao == "excluir")
        db.rollback.assert_called_once()

    @pytest.mark.parametrize(
        "inicio,regra,esperadas",
        [
            ("2027-01-01", "FREQ=DAILY;COUNT=3", ["2027-01-01", "2027-01-02", "2027-01-03"]),
            (
                "2027-01-04",
                "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE;COUNT=4",
                ["2027-01-04", "2027-01-06", "2027-01-18", "2027-01-20"],
            ),
            (
                "2027-01-31",
                "FREQ=MONTHLY;BYMONTHDAY=-1;COUNT=3",
                ["2027-01-31", "2027-02-28", "2027-03-31"],
            ),
            (
                "2027-01-12",
                "FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2;COUNT=3",
                ["2027-01-12", "2027-02-09", "2027-03-09"],
            ),
            (
                "2027-01-25",
                "FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-1;COUNT=3",
                ["2027-01-25", "2027-02-22", "2027-03-29"],
            ),
            ("2027-01-01", "FREQ=YEARLY;COUNT=3", ["2027-01-01", "2028-01-01", "2029-01-01"]),
            (
                "2027-01-01",
                "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;COUNT=3",
                ["2027-01-01", "2027-01-04", "2027-01-05"],
            ),
            ("2027-01-01", "FREQ=DAILY;UNTIL=20270102T235959", ["2027-01-01", "2027-01-02"]),
            ("2027-01-01", "FREQ=DAILY;COUNT=1", ["2027-01-01"]),
            ("2027-01-03", "FREQ=WEEKLY;BYDAY=MO;COUNT=2", ["2027-01-03", "2027-01-04"]),
        ],
    )
    def test_expandir(self, inicio, regra, esperadas):
        assert [
            d.date().isoformat() for d in datas_recorrentes(regra, datetime.fromisoformat(inicio))
        ] == esperadas

    @pytest.mark.parametrize("termino", ["", ";COUNT=999999", ";UNTIL=20991231T235959"])
    def test_limite_tres_anos(self, termino):
        datas = datas_recorrentes(f"FREQ=DAILY{termino}", datetime(2027, 1, 1))
        assert len(datas) == 1097
        assert datas[-1] == datetime(2030, 1, 1)

    @pytest.mark.parametrize(
        "regra",
        [
            "",
            "FREQ=SECONDLY",
            "FREQ=DAILY;INTERVAL=0",
            "FREQ=DAILY;COUNT=0",
            "FREQ=DAILY;COUNT=2;UNTIL=20270102T235959",
            "FREQ=DAILY;BYHOUR=10",
            "FREQ=MONTHLY;BYMONTHDAY=0",
            "FREQ=WEEKLY;BYDAY=INVALIDO",
            "FREQ=DAILY;FREQ=WEEKLY",
            "FREQ=DAILY\nRRULE:FREQ=DAILY",
            "FREQ=DAILY;UNTIL=20260101T235959",
            "FREQ=YEARLY;BYMONTH=13",
        ],
    )
    def test_rejeitar_regra_invalida(self, regra):
        with pytest.raises(ValueError, match="Regra de recorrência inválida"):
            datas_recorrentes(regra, datetime(2027, 1, 1))

    @pytest.mark.parametrize(
        "regra,antes,depois,esperadas",
        [
            (
                "FREQ=WEEKLY;BYDAY=MO;COUNT=8",
                "2027-01-04",
                "2027-01-06",
                ["2027-01-06", "2027-01-13"],
            ),
            (
                "FREQ=MONTHLY;BYMONTHDAY=15",
                "2027-01-15",
                "2027-01-31",
                ["2027-01-31", "2027-02-28"],
            ),
            (
                "FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2",
                "2027-01-12",
                "2027-01-20",
                ["2027-01-20", "2027-02-17"],
            ),
            (
                "FREQ=YEARLY;BYMONTH=1;BYMONTHDAY=1",
                "2027-01-01",
                "2027-02-10",
                ["2027-02-10", "2028-02-10"],
            ),
        ],
    )
    def test_reancorar_frequencia(self, regra, antes, depois, esperadas):
        inicio = datetime.fromisoformat(depois)
        nova = reancorar_regra(regra, datetime.fromisoformat(antes), inicio)
        assert [
            d.date().isoformat() for d in datas_recorrentes(nova + ";COUNT=2", inicio)
        ] == esperadas
