import pytest
from sqlalchemy.orm import Session

from app.atuacao.model import Atuacao
from app.cargo.model import Cargo
from app.core.seguranca import criar_token_acesso
from app.funcionario.model import Funcionario, StatusFuncionario


@pytest.fixture()
def token_admin_sistema(db_session: Session) -> str:
    cargo = Cargo(
        nome_cargo="Administrador Sistema",
        permissao={"configuracoes_sistema": True},
    )
    db_session.add(cargo)
    db_session.commit()

    admin = Funcionario(
        nome="Admin Sistema",
        email="admin.sistema@teste.com",
        cargo_id=cargo.cargo_id,
        status=StatusFuncionario.ATIVO,
    )
    db_session.add(admin)
    db_session.commit()

    return criar_token_acesso({"sub": str(admin.funcionario_id), "email": admin.email})


@pytest.fixture()
def token_sem_permissao(db_session: Session) -> str:
    cargo = Cargo(
        nome_cargo="Estagiário",
        permissao={"configuracoes_sistema": False},
    )
    db_session.add(cargo)
    db_session.commit()

    user = Funcionario(
        nome="Estagiário",
        email="estagiario@teste.com",
        cargo_id=cargo.cargo_id,
        status=StatusFuncionario.ATIVO,
    )
    db_session.add(user)
    db_session.commit()

    return criar_token_acesso({"sub": str(user.funcionario_id), "email": user.email})


@pytest.fixture()
def headers_admin(token_admin_sistema: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_admin_sistema}"}


@pytest.fixture()
def headers_comum(token_sem_permissao: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_sem_permissao}"}


@pytest.mark.parametrize(
    ("payload", "nome_esperado", "exibicao_esperada"),
    [
        (
            {
                "nome": "Direito Civil",
                "descricao": "Contratos, família e sucessões.",
                "exibicaoInstitucional": True,
            },
            "Direito Civil",
            True,
        ),
        (
            {
                "titulo": "  Direito Trabalhista  ",
                "descricao": "  Relações de trabalho e sindicatos.  ",
                "exibicaoInstitucional": False,
            },
            "Direito Trabalhista",
            False,
        ),
    ],
)
def test_criar_atuacao_parametrizado(
    client, headers_admin, payload, nome_esperado, exibicao_esperada
):
    response = client.post("/atuacoes", json=payload, headers=headers_admin)
    assert response.status_code == 201
    dados = response.json()
    assert dados["nome"] == nome_esperado
    assert dados["titulo"] == nome_esperado
    assert dados["exibicaoInstitucional"] == exibicao_esperada
    assert dados["atuacao_id"] > 0


def test_criar_atuacao_duplicada_retorna_400(client, headers_admin):
    payload = {"nome": "Direito Civil", "descricao": "Contratos e família."}
    assert client.post("/atuacoes", json=payload, headers=headers_admin).status_code == 201
    r = client.post("/atuacoes", json=payload, headers=headers_admin)
    assert r.status_code == 400
    assert r.json()["detail"] == "Área de atuação já cadastrada"


@pytest.mark.parametrize(
    "payload_invalido",
    [
        {"nome": "A", "descricao": "Descrição válida"},
        {"nome": "Direito Civil", "descricao": "X"},
        {"descricao": "Sem nome"},
    ],
)
def test_criar_atuacao_payload_invalido_retorna_422(client, headers_admin, payload_invalido):
    r = client.post("/atuacoes", json=payload_invalido, headers=headers_admin)
    assert r.status_code == 422


def test_listar_e_buscar_por_id(client, headers_admin):
    r_criado = client.post(
        "/atuacoes",
        json={"nome": "Direito Previdenciário", "descricao": "Aposentadorias e pensões."},
        headers=headers_admin,
    )
    atuacao_id = r_criado.json()["atuacao_id"]

    r_lista = client.get("/atuacoes")
    assert r_lista.status_code == 200
    assert len(r_lista.json()) == 1

    r_detalhe = client.get(f"/atuacoes/{atuacao_id}")
    assert r_detalhe.status_code == 200
    assert r_detalhe.json()["nome"] == "Direito Previdenciário"

    assert client.get("/atuacoes/999").status_code == 404


@pytest.mark.parametrize(
    ("payload_update", "nome_esperado", "descricao_esperada", "exibicao_esperada"),
    [
        (
            {"titulo": "Direito Tributário", "descricao": "Planejamento fiscal."},
            "Direito Tributário",
            "Planejamento fiscal.",
            True,
        ),
        (
            {"exibicaoInstitucional": False},
            "Direito Civil",
            "Descrição inicial.",
            False,
        ),
        (
            {"nome": "Direito Civil", "descricao": "Nova descrição."},
            "Direito Civil",
            "Nova descrição.",
            True,
        ),
    ],
)
def test_atualizar_atuacao_parametrizado(
    client,
    headers_admin,
    payload_update,
    nome_esperado,
    descricao_esperada,
    exibicao_esperada,
):
    criado = client.post(
        "/atuacoes",
        json={"nome": "Direito Civil", "descricao": "Descrição inicial."},
        headers=headers_admin,
    ).json()

    r = client.put(
        f"/atuacoes/{criado['atuacao_id']}",
        json=payload_update,
        headers=headers_admin,
    )
    assert r.status_code == 200
    dados = r.json()
    assert dados["nome"] == nome_esperado
    assert dados["descricao"] == descricao_esperada
    assert dados["exibicaoInstitucional"] == exibicao_esperada


def test_atualizar_atuacao_erros(client, headers_admin):
    a1 = client.post(
        "/atuacoes",
        json={"nome": "Direito Civil", "descricao": "Desc 1"},
        headers=headers_admin,
    ).json()
    client.post(
        "/atuacoes",
        json={"nome": "Direito Penal", "descricao": "Desc 2"},
        headers=headers_admin,
    )

    assert (
        client.put(
            f"/atuacoes/{a1['atuacao_id']}",
            json={"nome": "Direito Penal"},
            headers=headers_admin,
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/atuacoes/999",
            json={"nome": "Outro"},
            headers=headers_admin,
        ).status_code
        == 404
    )


@pytest.mark.parametrize("novo_valor", [False, True])
def test_mudar_exibicao_institucional(client, headers_admin, novo_valor):
    criado = client.post(
        "/atuacoes",
        json={"nome": "Direito Empresarial", "descricao": "Contratos societários."},
        headers=headers_admin,
    ).json()

    r = client.patch(
        f"/atuacoes/{criado['atuacao_id']}/exibicao-institucional",
        json={"exibicaoInstitucional": novo_valor},
        headers=headers_admin,
    )
    assert r.status_code == 200
    assert r.json()["exibicaoInstitucional"] is novo_valor

    assert (
        client.patch(
            "/atuacoes/999/exibicao-institucional",
            json={"exibicaoInstitucional": False},
            headers=headers_admin,
        ).status_code
        == 404
    )


def test_deletar_atuacao(client, headers_admin):
    criado = client.post(
        "/atuacoes",
        json={"nome": "Direito Ambiental", "descricao": "Licenciamento ambiental."},
        headers=headers_admin,
    ).json()

    r_del = client.delete(f"/atuacoes/{criado['atuacao_id']}", headers=headers_admin)
    assert r_del.status_code == 200
    assert (
        client.delete(f"/atuacoes/{criado['atuacao_id']}", headers=headers_admin).status_code == 404
    )


@pytest.mark.parametrize(
    ("metodo", "rota", "json_body"),
    [
        ("POST", "/atuacoes", {"nome": "Civil", "descricao": "Desc"}),
        ("PUT", "/atuacoes/1", {"nome": "Civil"}),
        ("PATCH", "/atuacoes/1/exibicao-institucional", {"exibicaoInstitucional": False}),
        ("DELETE", "/atuacoes/1", None),
    ],
)
def test_rotas_protegidas_atuacao(client, headers_comum, metodo, rota, json_body):
    r_sem_token = client.request(metodo, rota, json=json_body)
    assert r_sem_token.status_code == 401

    r_sem_permissao = client.request(metodo, rota, json=json_body, headers=headers_comum)
    assert r_sem_permissao.status_code == 403


def test_obter_atuacoes_publicas_institucional(client, db_session: Session):
    db_session.add_all(
        [
            Atuacao(
                nome="Direito Civil",
                descricao="Visível no site",
                exibicao_institucional=True,
            ),
            Atuacao(
                nome="Direito Oculto",
                descricao="Não visível no site",
                exibicao_institucional=False,
            ),
        ]
    )
    db_session.commit()

    r = client.get("/institucional/atuacoes")
    assert r.status_code == 200
    dados = r.json()
    assert len(dados) == 1
    assert dados[0]["nome"] == "Direito Civil"
    assert dados[0]["titulo"] == "Direito Civil"
