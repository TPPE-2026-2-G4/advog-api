from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.cliente.model import Cliente
from app.cliente.repository import ClienteRepository
from app.config.database import Base, SessionLocal, engine
from app.config.limiter import limiter
from app.core.dependencies import obter_funcionario_atual
from main import app

Base.metadata.create_all(bind=engine)


def _funcionario_com(permissao: dict[str, bool]) -> SimpleNamespace:
    return SimpleNamespace(
        funcionario_id=1, email="test@test.com", cargo=SimpleNamespace(permissao=permissao)
    )


def override_obter_funcionario_atual():
    return _funcionario_com({"gerenciar_clientes": True})


client = TestClient(app)


def setup_function():
    app.dependency_overrides[obter_funcionario_atual] = override_obter_funcionario_atual
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Cliente).delete()
    db.commit()

    c1 = Cliente(
        nome="Cliente Teste 1",
        telefone="(11) 91111-1111",
        email="cliente1@teste.com",
        area_interesse="Civil",
        documento="12345678901",
        ultima_interacao=datetime(2026, 1, 1),
        responsavel_id=1,
        etapa_id=1,
    )
    c2 = Cliente(
        nome="Cliente Teste 2",
        telefone="(22) 92222-2222",
        email="cliente2@teste.com",
        area_interesse="Trabalhista",
        documento="98765432000199",
        ultima_interacao=datetime(2026, 2, 1),
        responsavel_id=2,
        etapa_id=2,
    )

    db.add(c1)
    db.add(c2)
    db.commit()
    db.close()


def teardown_function():
    app.dependency_overrides.clear()
    db = SessionLocal()
    db.query(Cliente).delete()
    db.commit()
    db.close()


def test_listar_clientes():
    response = client.get("/clientes/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def _criar_clientes_extras(quantidade: int) -> None:
    db = SessionLocal()
    for indice in range(quantidade):
        db.add(
            Cliente(
                nome=f"Extra {indice}",
                telefone="(33) 93333-3333",
                email=f"extra{indice}@teste.com",
                ultima_interacao=datetime(2026, 3, 1),
                responsavel_id=3,
                etapa_id=3,
            )
        )
    db.commit()
    db.close()


def test_listar_clientes_paginado_retorna_metadados_e_ordem_decrescente():
    _criar_clientes_extras(3)

    response = client.get("/clientes/paginado?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3
    assert len(data["itens"]) == 2
    ids = [item["cliente_id"] for item in data["itens"]]
    assert ids == sorted(ids, reverse=True)


def test_listar_clientes_paginado_ultima_pagina_tem_itens_restantes():
    _criar_clientes_extras(3)

    pagina_1 = client.get("/clientes/paginado?page=1&page_size=2").json()
    pagina_3 = client.get("/clientes/paginado?page=3&page_size=2").json()
    pagina_4 = client.get("/clientes/paginado?page=4&page_size=2").json()

    assert len(pagina_3["itens"]) == 1
    assert pagina_4["itens"] == []
    assert pagina_4["total"] == 5
    ids_pagina_1 = {item["cliente_id"] for item in pagina_1["itens"]}
    assert pagina_3["itens"][0]["cliente_id"] not in ids_pagina_1


def test_listar_clientes_paginado_aplica_filtros_antes_de_paginar():
    _criar_clientes_extras(3)

    response = client.get("/clientes/paginado?busca=Extra&etapa_id=3&page_size=2")

    data = response.json()
    assert data["total"] == 3
    assert data["total_pages"] == 2
    assert all(item["nome"].startswith("Extra") for item in data["itens"])

    response = client.get("/clientes/paginado?responsavel_id=1")
    assert response.json()["total"] == 1


@pytest.mark.parametrize(
    "busca",
    ["123.456.789-00", "12345678900", "123456789", "123 456"],
)
def test_busca_por_documento_ignora_pontuacao(busca):
    db = SessionLocal()
    db.add(
        Cliente(
            nome="Com Máscara",
            telefone="(44) 94444-4444",
            email="mascara@teste.com",
            documento="123.456.789-00",
            ultima_interacao=datetime(2026, 3, 1),
            etapa_id=1,
        )
    )
    db.commit()
    db.close()

    nomes = [i["nome"] for i in client.get(f"/clientes/paginado?busca={busca}").json()["itens"]]

    assert "Com Máscara" in nomes


def test_busca_por_documento_formatado_encontra_documento_sem_mascara():
    nomes = [
        i["nome"] for i in client.get("/clientes/paginado?busca=123.456.789-01").json()["itens"]
    ]

    assert nomes == ["Cliente Teste 1"]


def test_busca_com_texto_e_digitos_nao_vira_busca_de_documento():
    # "1" aparece em ambos os documentos, mas "Teste 1" é busca por nome, não por documento.
    nomes = [i["nome"] for i in client.get("/clientes/paginado?busca=Teste 1").json()["itens"]]

    assert nomes == ["Cliente Teste 1"]


def test_listar_clientes_paginado_sem_resultados_tem_uma_pagina():
    response = client.get("/clientes/paginado?busca=inexistente")

    assert response.status_code == 200
    assert response.json() == {
        "itens": [],
        "total": 0,
        "page": 1,
        "page_size": 10,
        "total_pages": 1,
    }


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101"])
def test_listar_clientes_paginado_rejeita_parametros_invalidos(query):
    assert client.get(f"/clientes/paginado?{query}").status_code == 422


def test_listar_clientes_paginado_exige_autenticacao():
    app.dependency_overrides.pop(obter_funcionario_atual, None)

    assert client.get("/clientes/paginado").status_code == 401


def test_filtrar_clientes_por_busca_nome():
    response = client.get("/clientes/?busca=Teste 1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nome"] == "Cliente Teste 1"


def test_filtrar_clientes_por_busca_email():
    response = client.get("/clientes/?busca=cliente2@teste.com")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == "cliente2@teste.com"


def test_filtrar_clientes_por_responsavel():
    response = client.get("/clientes/?responsavel_id=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["responsavel_id"] == 2


def test_filtrar_clientes_por_etapa():
    response = client.get("/clientes/?etapa_id=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["etapa_id"] == 1


def test_criar_cliente():
    payload = {
        "nome": "Novo Cliente 3",
        "telefone": "(33) 93333-3333",
        "email": "novo@teste.com",
        "area_interesse": "Tributário",
        "descricao": "Precisa de consultoria para revisão tributária",
        "ultima_interacao": "2026-03-01T00:00:00",
        "responsavel_id": 1,
        "etapa_id": 1,
    }
    response = client.post("/clientes/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Novo Cliente 3"
    assert data["area_interesse"] == "Tributário"
    assert data["descricao"] == "Precisa de consultoria para revisão tributária"
    assert data["cliente_id"] is not None


def test_obter_cliente_por_id():
    response = client.get("/clientes/")
    data = response.json()
    cliente_id = data[0]["cliente_id"]

    response2 = client.get(f"/clientes/{cliente_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cliente_id"] == cliente_id
    assert data2["nome"] == data[0]["nome"]


def test_obter_cliente_inexistente():
    response = client.get("/clientes/999999")
    assert response.status_code == 404


def test_atualizar_cliente_sucesso():
    db = SessionLocal()
    repositorio = ClienteRepository(db)
    cliente = db.query(Cliente).first()
    assert cliente is not None

    dados_atualizacao = {"nome": "Cliente Teste Alterado", "telefone": "(11) 98888-8888"}
    cliente_atualizado = repositorio.update(cliente.cliente_id, dados_atualizacao)

    assert cliente_atualizado is not None
    assert cliente_atualizado.nome == "Cliente Teste Alterado"
    assert cliente_atualizado.telefone == "(11) 98888-8888"
    db.close()


def test_atualizar_cliente_inexistente_retorna_none():
    db = SessionLocal()
    repositorio = ClienteRepository(db)
    resultado = repositorio.update(99999, {"nome": "Inexistente"})

    assert resultado is None
    db.close()


def test_deletar_cliente_sucesso():
    db = SessionLocal()
    repositorio = ClienteRepository(db)
    cliente = db.query(Cliente).first()
    assert cliente is not None

    sucesso = repositorio.delete(cliente.cliente_id)
    cliente_buscado = repositorio.get_by_id(cliente.cliente_id)

    assert sucesso is True
    assert cliente_buscado is None
    db.close()


def test_deletar_cliente_inexistente_retorna_false():
    db = SessionLocal()
    repositorio = ClienteRepository(db)
    sucesso = repositorio.delete(99999)

    assert sucesso is False
    db.close()


def test_atualizar_cliente():
    response = client.get("/clientes/")
    cliente_id = response.json()[0]["cliente_id"]

    payload = {
        "nome": "Cliente Atualizado",
        "telefone": "(11) 98888-8888",
        "email": "atualizado@teste.com",
        "area_interesse": "Empresarial",
        "descricao": "Demanda alterada para societário",
        "ultima_interacao": "2026-04-01T00:00:00",
        "responsavel_id": 2,
        "etapa_id": 3,
    }
    response = client.put(f"/clientes/{cliente_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "Cliente Atualizado"
    assert data["area_interesse"] == "Empresarial"
    assert data["descricao"] == "Demanda alterada para societário"
    assert data["etapa_id"] == 3


def test_excluir_cliente():
    response = client.get("/clientes/")
    cliente_id = response.json()[0]["cliente_id"]

    response = client.delete(f"/clientes/{cliente_id}")
    assert response.status_code == 204

    response_check = client.get(f"/clientes/{cliente_id}")
    assert response_check.status_code == 404


def test_filtrar_clientes_por_busca_documento():
    response = client.get("/clientes/?busca=12345678901")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nome"] == "Cliente Teste 1"
    assert data[0]["documento"] == "12345678901"


def test_criar_cliente_com_documento():
    payload = {
        "nome": "Cliente com Documento",
        "telefone": "(44) 94444-4444",
        "email": "comdoc@teste.com",
        "area_interesse": "Ambiental",
        "descricao": "Licenciamento",
        "documento": "11122233344",
        "ultima_interacao": "2026-03-01T00:00:00",
        "responsavel_id": 1,
        "etapa_id": 1,
    }
    response = client.post("/clientes/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Cliente com Documento"
    assert data["documento"] == "11122233344"


def test_atualizar_cliente_com_documento():
    response = client.get("/clientes/")
    cliente_id = response.json()[0]["cliente_id"]

    payload = {
        "nome": "Cliente Atualizado com Doc",
        "telefone": "(11) 98888-8888",
        "email": "atualizado_doc@teste.com",
        "area_interesse": "Empresarial",
        "descricao": "Alterado",
        "documento": "55566677788",
        "ultima_interacao": "2026-04-01T00:00:00",
        "responsavel_id": 2,
        "etapa_id": 3,
    }
    response = client.put(f"/clientes/{cliente_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["documento"] == "55566677788"


def test_atualizar_cliente_inexistente():
    payload = {
        "nome": "Inexistente",
        "telefone": "(11) 99999-9999",
        "email": "inexistente@teste.com",
        "area_interesse": "Civil",
        "descricao": "Nao existe",
        "documento": "00000000000",
        "ultima_interacao": "2026-04-01T00:00:00",
        "responsavel_id": 1,
        "etapa_id": 1,
    }
    response = client.put("/clientes/999999", json=payload)
    assert response.status_code == 404


def test_excluir_cliente_inexistente():
    response = client.delete("/clientes/999999")
    assert response.status_code == 404


def test_criar_cliente_sem_telefone_retorna_422():
    payload = {
        "nome": "Sem Telefone",
        "email": "sem.telefone@teste.com",
        "ultima_interacao": "2026-03-01T00:00:00",
        "etapa_id": 1,
    }

    assert client.post("/clientes/", json=payload).status_code == 422


def test_clientes_com_mesmo_email_sao_permitidos():
    payload = {
        "nome": "Cliente Repetido",
        "telefone": "(44) 94444-4444",
        "email": "repetido@teste.com",
        "descricao": "Primeira solicitação",
        "ultima_interacao": "2026-03-01T00:00:00",
        "etapa_id": 1,
    }

    primeiro = client.post("/clientes/", json=payload)
    segundo = client.post("/clientes/", json={**payload, "descricao": "Segunda solicitação"})

    assert primeiro.status_code == segundo.status_code == 201
    assert primeiro.json()["cliente_id"] != segundo.json()["cliente_id"]


@pytest.fixture(autouse=True)
def reiniciar_limitador():
    limiter.reset()
    yield
    limiter.reset()


def _solicitacao(**campos) -> dict:
    return {
        "nome": "Fernanda Lima",
        "email": "fernanda@email.com",
        "telefone": "(61) 98888-5555",
        "descricao": "Gostaria de agendar uma consulta sobre causa trabalhista.",
        **campos,
    }


def test_criar_cliente_nao_exige_autenticacao_e_usa_valores_padrao():
    app.dependency_overrides.pop(obter_funcionario_atual)

    response = client.post("/clientes/", json=_solicitacao())

    assert response.status_code == 201
    data = response.json()
    assert data["etapa_id"] == 1
    assert data["responsavel_id"] is None
    assert data["ultima_interacao"] is not None
    assert data["descricao"] == "Gostaria de agendar uma consulta sobre causa trabalhista."


def test_demais_rotas_de_cliente_continuam_exigindo_autenticacao():
    app.dependency_overrides.pop(obter_funcionario_atual)

    assert client.get("/clientes/").status_code == 401
    assert client.get("/clientes/1").status_code == 401
    assert client.put("/clientes/1", json={}).status_code == 401
    assert client.delete("/clientes/1").status_code == 401


def test_criar_cliente_limita_requisicoes_por_minuto():
    respostas = [client.post("/clientes/", json=_solicitacao()) for _ in range(6)]

    assert [r.status_code for r in respostas] == [201, 201, 201, 201, 201, 429]


@pytest.mark.parametrize(
    "campos",
    [
        {"nome": ""},
        {"nome": "N" * 101},
        {"email": "email_sem_dominio"},
        {"telefone": "1" * 17},
        {"descricao": "D" * 2001},
        {"documento": "1" * 21},
    ],
)
def test_criar_cliente_rejeita_dados_invalidos(campos):
    assert client.post("/clientes/", json=_solicitacao(**campos)).status_code == 422


@pytest.mark.parametrize(
    ("permissao", "leitura", "escrita"),
    [
        ({}, 403, 403),
        ({"gerenciar_equipe": True, "gerenciar_site": True}, 403, 403),
        ({"visualizar_clientes": True}, 200, 403),
        ({"gerenciar_clientes": True}, 200, 200),
    ],
)
def test_leitura_e_escrita_de_clientes_respeitam_permissoes(permissao, leitura, escrita):
    app.dependency_overrides[obter_funcionario_atual] = lambda: _funcionario_com(permissao)
    existente = client.get("/clientes/").json()[0]["cliente_id"] if leitura == 200 else 1

    assert client.get("/clientes/").status_code == leitura
    assert client.get(f"/clientes/{existente}").status_code == leitura
    # com permissão, o 404/422 prova que a requisição passou pelo controle de acesso
    assert client.delete("/clientes/999999").status_code == (404 if escrita == 200 else 403)
    assert client.put("/clientes/999999", json={}).status_code == (422 if escrita == 200 else 403)


def test_criar_cliente_continua_publico_mesmo_sem_permissoes():
    app.dependency_overrides[obter_funcionario_atual] = lambda: _funcionario_com({})

    assert client.post("/clientes/", json=_solicitacao()).status_code == 201


@pytest.mark.parametrize(
    ("permissao", "leitura"),
    [
        ({"visualizar_processos": True}, 200),
        ({"gerenciar_processos": True}, 200),
        ({"visualizar_atividades": True}, 403),
        ({"visualizar_financeiro": True}, 403),
    ],
)
def test_lista_de_clientes_atende_a_tela_de_processos(permissao, leitura):
    app.dependency_overrides[obter_funcionario_atual] = lambda: _funcionario_com(permissao)

    assert client.get("/clientes/").status_code == leitura


def test_permissao_de_processos_nao_altera_nem_exclui_clientes():
    app.dependency_overrides[obter_funcionario_atual] = lambda: _funcionario_com(
        {"visualizar_processos": True, "gerenciar_processos": True}
    )

    assert client.put("/clientes/1", json={}).status_code == 403
    assert client.delete("/clientes/1").status_code == 403
