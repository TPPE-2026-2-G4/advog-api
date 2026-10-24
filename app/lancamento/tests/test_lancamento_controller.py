from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(client: TestClient, token_admin: str) -> TestClient:
    client.headers["Authorization"] = f"Bearer {token_admin}"
    return client


def _payload_lancamento(**kwargs) -> dict:
    base = {
        "titulo": "Honorários Advocatícios",
        "tipo": "e",
        "valor": 1200.0,
        "data_vencimento": (datetime.now() + timedelta(days=5)).isoformat(),
    }
    return {**base, **kwargs}


def _dias(n: int) -> str:
    return (datetime.now() + timedelta(days=n)).isoformat()


def _popular(client: TestClient) -> None:
    client.post("/lancamentos/", json=_payload_lancamento(titulo="pendente", valor=100))
    feito = client.post(
        "/lancamentos/",
        json=_payload_lancamento(titulo="feito", tipo="s", valor=50, data_vencimento=_dias(-10)),
    ).json()
    client.patch(f"/lancamentos/{feito['lancamento_id']}/alternar-status")
    client.post(
        "/lancamentos/",
        json=_payload_lancamento(titulo="atrasado", valor=200, data_vencimento=_dias(-3)),
    )


class TestLancamentoControllerCRUD:
    def test_criar_e_buscar_lancamento(self, client: TestClient):
        response_criar = client.post("/lancamentos/", json=_payload_lancamento())
        assert response_criar.status_code == 201
        dados_criados = response_criar.json()
        assert dados_criados["titulo"] == "Honorários Advocatícios"

        lid = dados_criados["lancamento_id"]
        response_listar = client.get("/lancamentos/")
        assert response_listar.status_code == 200
        assert any(item["lancamento_id"] == lid for item in response_listar.json())

    def test_criar_lancamento_com_categoria(self, client: TestClient):
        cat = client.post("/categorias-lancamento", json={"nome_categoria": "Honorários"}).json()
        payload = _payload_lancamento(categoria_id=cat["categoria_id"])
        response = client.post("/lancamentos/", json=payload)
        assert response.status_code == 201
        dados = response.json()
        assert dados["status"] == "Pendente"
        assert dados["data_pagamento"] is None
        assert dados["categoria_id"] == cat["categoria_id"]

    def test_criar_lancamento_tipo_invalido(self, client: TestClient):
        response = client.post("/lancamentos/", json=_payload_lancamento(tipo="x"))
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "payload_extra,status_esperado,mensagem_erro",
        [
            ({"categoria_id": 999999}, 404, "Categoria não encontrada"),
            ({"cliente_id": 999999}, 404, "Cliente não encontrado"),
        ],
    )
    def test_criar_lancamento_com_referencias_invalidas_retorna_404(
        self, client: TestClient, payload_extra: dict, status_esperado: int, mensagem_erro: str
    ):
        payload = _payload_lancamento(**payload_extra)
        response = client.post("/lancamentos/", json=payload)

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
        self, client: TestClient, metodo: str, endpoint: str, json_body: dict | None
    ):
        funcao_http = getattr(client, metodo)
        kwargs = {"json": json_body} if json_body else {}
        response = funcao_http(endpoint, **kwargs)

        assert response.status_code == 404
        assert response.json()["detail"] == "Lançamento não encontrado"

    def test_atualizar_lancamento_sucesso_e_campo_nulo_retorna_400(self, client: TestClient):
        lid = client.post("/lancamentos/", json=_payload_lancamento()).json()["lancamento_id"]

        response_atualizar = client.put(
            f"/lancamentos/{lid}", json={"titulo": "Honorários Revisados"}
        )
        assert response_atualizar.status_code == 200
        assert response_atualizar.json()["titulo"] == "Honorários Revisados"

        response_nulo = client.put(f"/lancamentos/{lid}", json={"titulo": None})
        assert response_nulo.status_code == 400

    def test_alternar_status_sucesso(self, client: TestClient):
        lid = client.post("/lancamentos/", json=_payload_lancamento()).json()["lancamento_id"]

        response_alternar = client.patch(f"/lancamentos/{lid}/alternar-status")
        assert response_alternar.status_code == 200
        assert response_alternar.json()["status"] == "Realizado"

    def test_rota_de_status_manual_removida(self, client: TestClient):
        lid = client.post("/lancamentos/", json=_payload_lancamento()).json()["lancamento_id"]
        response = client.patch(f"/lancamentos/{lid}/status", json={"status": "Realizado"})
        assert response.status_code in (404, 405)

    def test_remover_lancamento_sucesso(self, client: TestClient):
        lid = client.post("/lancamentos/", json=_payload_lancamento()).json()["lancamento_id"]

        response_deletar = client.delete(f"/lancamentos/{lid}")
        assert response_deletar.status_code == 204
        assert client.delete(f"/lancamentos/{lid}").status_code == 404


class TestLancamentoControllerConsultasEResumo:
    def test_filtrar_por_status(self, client: TestClient):
        _popular(client)
        for status, titulo in [
            ("Pendente", "pendente"),
            ("Realizado", "feito"),
            ("Atrasado", "atrasado"),
        ]:
            response = client.get("/lancamentos/", params={"status": status})
            assert response.status_code == 200
            assert [item["titulo"] for item in response.json()] == [titulo]

    def test_filtrar_por_periodo(self, client: TestClient):
        _popular(client)
        hoje = datetime.now().date()
        response = client.get(
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
        self, client: TestClient, endpoint: str, params: dict
    ):
        response = client.get(endpoint, params=params)
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
    def test_grafico_parametros_invalidos_retornam_422(self, client: TestClient, params: dict):
        response = client.get("/lancamentos/grafico", params=params)
        assert response.status_code == 422

    def test_listar_paginado_sucesso(self, client: TestClient):
        _popular(client)
        response_paginado = client.get("/lancamentos/paginado", params={"page": 1, "page_size": 2})
        assert response_paginado.status_code == 200
        data = response_paginado.json()
        assert data["total"] == 3 and data["total_pages"] == 2
        assert [item["titulo"] for item in data["itens"]] == ["feito", "atrasado"]

        data_p2 = client.get("/lancamentos/paginado", params={"page": 2, "page_size": 2}).json()
        assert [item["titulo"] for item in data_p2["itens"]] == ["pendente"]

    def test_listar_paginado_com_filtros(self, client: TestClient):
        _popular(client)
        data = client.get("/lancamentos/paginado", params={"status": "Atrasado"}).json()
        assert data["total"] == 1 and data["itens"][0]["titulo"] == "atrasado"
        vazio = client.get(
            "/lancamentos/paginado", params={"tipo": "s", "status": "Pendente"}
        ).json()
        assert vazio == {"itens": [], "total": 0, "page": 1, "page_size": 10, "total_pages": 1}

    def test_listar_paginado_validacoes(self, client: TestClient):
        assert client.get("/lancamentos/paginado", params={"page": 0}).status_code == 422
        assert client.get("/lancamentos/paginado", params={"page_size": 101}).status_code == 422
        r = client.get(
            "/lancamentos/paginado", params={"inicio": "2026-10-10", "fim": "2026-10-01"}
        )
        assert r.status_code == 400

    def test_resumir_lancamentos_sucesso(self, client: TestClient):
        client.post("/lancamentos/", json=_payload_lancamento())

        response_resumo = client.get("/lancamentos/resumo")
        assert response_resumo.status_code == 200
        data = response_resumo.json()
        assert "pendente" in data

    def test_obter_grafico_sucesso(self, client: TestClient):
        _popular(client)
        response = client.get("/lancamentos/grafico")
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
        self, client: TestClient, params: dict, status_code_esperado: int
    ):
        response = client.get("/lancamentos/calendario", params=params)
        assert response.status_code == status_code_esperado

    def test_exportar_icalendar_sucesso_headers(self, client: TestClient):
        client.post("/lancamentos/", json=_payload_lancamento(titulo="Atendimento 1"))

        params_ok = {"inicio": "2026-10-01", "fim": "2026-10-31"}
        response = client.get("/lancamentos/calendario/exportar", params=params_ok)

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
