from unittest.mock import MagicMock, patch

import pytest

from app.arquivo.model import Arquivo
from app.arquivo.repository import ArquivoRepository
from app.atuacao.model import Atuacao
from app.atuacao.repository import AtuacaoRepository
from app.cargo.model import Cargo
from app.cargo.repository import CargoRepository
from app.funcionario.model import Funcionario, StatusFuncionario
from app.funcionario.repository import FuncionarioRepository
from app.funcionario.schema import FuncionarioCreate, FuncionarioPrimeiroAcesso, FuncionarioUpdate
from app.funcionario.service import FuncionarioService


@pytest.fixture
def outro_cargo(db_session):
    cargo = Cargo(nome_cargo="Sócio", descricao="Cargo de teste", permissao={})
    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)
    return cargo


class TestCriarFuncionarioController:
    @pytest.mark.parametrize(
        "nome,email",
        [
            ("Ana Beatriz Souza", "ana.souza@test.com"),
            ("Carlos Eduardo Lima", "carlos.lima@test.com"),
            ("Patrícia Almeida", "patricia.almeida@test.com"),
            ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
            ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
        ],
    )
    def test_criar_funcionario_retorna_funcionario_criado(
        self, client, cargo_padrao, atuacao_padrao, nome, email, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": nome,
                "email": email,
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["nome"] == nome
        assert response.json()["email"] == email.lower()
        assert response.json()["cargo_id"] == cargo_padrao.cargo_id

    def test_criar_funcionario_com_cargo_inexistente_retorna_erro(
        self, client, token_admin, atuacao_padrao
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Existente",
                "email": "funcionario.existente@test.com",
                "cargo_id": 9999,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Cargo não encontrado"

    def test_criar_funcionario_com_atuacao_inexistente_retorna_erro(
        self, client, token_admin, cargo_padrao
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Sem Atuacao",
                "email": "sem.atuacao@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": 9999,
            },
            headers=headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Área de atuação não encontrada"

    def test_criar_funcionario_sem_atuacao_retorna_422(self, client, token_admin, cargo_padrao):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Sem Atuacao",
                "email": "sem.atuacao@test.com",
                "cargo_id": cargo_padrao.cargo_id,
            },
            headers=headers,
        )
        assert response.status_code == 422

    def test_criar_funcionario_usa_foto_de_perfil_padrao(
        self, client, db_session, token_admin, cargo_padrao, atuacao_padrao
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        primeiro = client.post(
            "/funcionarios",
            json={
                "nome": "Primeiro",
                "email": "primeiro@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        ).json()
        segundo = client.post(
            "/funcionarios",
            json={
                "nome": "Segundo",
                "email": "segundo@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        ).json()

        assert primeiro["foto_perfil"] == segundo["foto_perfil"]
        assert primeiro["atuacao_id"] == atuacao_padrao.atuacao_id
        assert db_session.get(Arquivo, primeiro["foto_perfil"]).bucket_link == ""

    def test_criar_funcionario_com_email_existente_retorna_erro(
        self, client, cargo_padrao, atuacao_padrao, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Existente",
                "email": "funcionario.existente@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201

        response_erro = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Existente 2",
                "email": "funcionario.existente@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )

        assert response_erro.status_code == 400
        assert response_erro.json()["detail"] == "Email já cadastrado"


class TestBuscarFuncionariosController:
    def test_buscar_todos_funcionarios_com_funcionarios_cadastrados_retorna_lista(
        self, client, cargo_padrao, atuacao_padrao, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario 1",
                "email": "funcionario.1@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario 2",
                "email": "funcionario.2@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201

        response = client.get("/funcionarios", headers=headers)
        assert response.status_code == 200
        funcionarios = response.json()
        emails = [f["email"] for f in funcionarios]
        assert "funcionario.1@test.com" in emails
        assert "funcionario.2@test.com" in emails
        assert isinstance(funcionarios, list)

    def test_buscar_todos_funcionarios_sem_funcionarios_cadastrados_retorna_lista_vazia(
        self, client, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.get("/funcionarios", headers=headers)
        assert response.status_code == 200
        funcionarios = [f for f in response.json() if f["email"] != "admin.fixture@test.com"]
        assert funcionarios == []


class TestPrimeiroAcessoController:
    @pytest.mark.parametrize(
        "nome,email",
        [
            ("Ana Beatriz Souza", "ana.souza@test.com"),
            ("Carlos Eduardo Lima", "carlos.lima@test.com"),
            ("Patrícia Almeida", "patricia.almeida@test.com"),
            ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
            ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
        ],
    )
    def test_primeiro_acesso_retorna_funcionario_atualizado(
        self, client, cargo_padrao, atuacao_padrao, token_primeiro_acesso, nome, email, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": nome,
                "email": email,
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["nome"] == nome
        assert response.json()["email"] == email.lower()
        assert response.json()["status"] == StatusFuncionario.PENDENTE.value

        funcionario_id = response.json()["funcionario_id"]
        response = client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": "senha123", "token": token_primeiro_acesso(funcionario_id)},
        )
        assert response.status_code == 200
        assert response.json()["nome"] == nome
        assert response.json()["email"] == email.lower()
        assert response.json()["status"] == StatusFuncionario.ATIVO.value

    def test_primeiro_acesso_funcionario_nao_encontrado_retorna_erro(
        self, client, token_primeiro_acesso
    ):
        response = client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": "senha123", "token": token_primeiro_acesso(999)},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário não encontrado"

    def test_primeiro_acesso_funcionario_ja_ativado_retorna_erro(
        self, client, cargo_padrao, atuacao_padrao, token_primeiro_acesso, token_admin, db_session
    ):
        admin = db_session.query(Funcionario).filter_by(email="admin.fixture@test.com").first()
        if admin:
            admin.status = StatusFuncionario.ATIVO
            if admin.cargo:
                admin.cargo.permissao = {"gerenciar_equipe": True}
            db_session.commit()

        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Ativo",
                "email": "funcionario.ativo@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201

        funcionario_id = response.json()["funcionario_id"]
        token = token_primeiro_acesso(funcionario_id)
        response = client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": "senha123", "token": token},
        )
        assert response.status_code == 200

        response = client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": "senha456", "token": token},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário já teve a conta ativada"

    def test_primeiro_acesso_token_invalido_retorna_401(self, client):
        response = client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": "senha123", "token": "token_invalido_malformado"},
        )
        assert response.status_code == 401
        assert "inválido" in response.json()["detail"].lower()


class TestMudarAcessoController:
    @pytest.mark.parametrize(
        "nome,email",
        [
            ("Ana Beatriz Souza", "ana.souza@test.com"),
            ("Carlos Eduardo Lima", "carlos.lima@test.com"),
            ("Patrícia Almeida", "patricia.almeida@test.com"),
            ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
            ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
        ],
    )
    def test_mudar_acesso_funcionario_muda_atividade_e_manda_funcionario_atualizado(
        self, client, cargo_padrao, atuacao_padrao, token_primeiro_acesso, nome, email, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": nome,
                "email": email,
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201

        funcionario_id = response.json()["funcionario_id"]
        response = client.patch(
            "/funcionarios/primeiro-acesso",
            json={"senha": "senha123", "token": token_primeiro_acesso(funcionario_id)},
        )
        assert response.status_code == 200

        response = client.patch(f"/funcionarios/{funcionario_id}/mudar-acesso", headers=headers)
        assert response.status_code == 200
        assert response.json()["nome"] == nome
        assert response.json()["email"] == email.lower()
        assert response.json()["status"] == StatusFuncionario.INATIVO.value

        response = client.patch(f"/funcionarios/{funcionario_id}/mudar-acesso", headers=headers)
        assert response.status_code == 200
        assert response.json()["nome"] == nome
        assert response.json()["email"] == email.lower()
        assert response.json()["status"] == StatusFuncionario.ATIVO.value

    def test_mudar_acesso_funcionario_nao_encontrado_retorna_erro(self, client, token_admin):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.patch("/funcionarios/999/mudar-acesso", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário não encontrado"

    def test_mudar_acesso_funcionario_com_conta_pendente_retorna_erro(
        self, client, cargo_padrao, atuacao_padrao, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Pendente",
                "email": "funcionario.pendente@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201

        funcionario_id = response.json()["funcionario_id"]
        response = client.patch(f"/funcionarios/{funcionario_id}/mudar-acesso", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário ainda não ativou a conta"

    def test_mudar_acesso_funcionario_inexistente_retorna_400(self, client, token_admin):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.patch("/funcionarios/9999/mudar-acesso", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário não encontrado"


class TestMudarCargoController:
    def test_mudar_cargo_retorna_funcionario_atualizado(
        self, client, cargo_padrao, atuacao_padrao, outro_cargo, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Teste",
                "email": "funcionario.cargo@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201
        funcionario_id = response.json()["funcionario_id"]

        response = client.patch(
            f"/funcionarios/{funcionario_id}/mudar-cargo",
            json={"cargo_id": outro_cargo.cargo_id},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["cargo_id"] == outro_cargo.cargo_id

    def test_mudar_cargo_funcionario_nao_encontrado_retorna_erro(
        self, client, cargo_padrao, atuacao_padrao, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.patch(
            "/funcionarios/999/mudar-cargo",
            json={"cargo_id": cargo_padrao.cargo_id},
            headers=headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário não encontrado"

    def test_mudar_cargo_com_cargo_inexistente_retorna_erro(
        self, client, cargo_padrao, atuacao_padrao, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Teste",
                "email": "funcionario.cargo2@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201
        funcionario_id = response.json()["funcionario_id"]

        response = client.patch(
            f"/funcionarios/{funcionario_id}/mudar-cargo",
            json={"cargo_id": 9999},
            headers=headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Cargo não encontrado"


class TestMudarExibicaoInstitucionalController:
    def test_mudar_exibicao_institucional_sucesso(
        self, client, cargo_padrao, atuacao_padrao, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        res = client.post(
            "/funcionarios",
            json={
                "nome": "Func Exibicao",
                "email": "exibicao@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        func_id = res.json()["funcionario_id"]

        response = client.patch(
            f"/funcionarios/{func_id}/exibicao-institucional",
            json={"exibicaoInstitucional": True},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["exibicaoInstitucional"] is True

    def test_mudar_exibicao_institucional_funcionario_inexistente_retorna_400(
        self, client, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.patch(
            "/funcionarios/9999/exibicao-institucional",
            json={"exibicaoInstitucional": True},
            headers=headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário não encontrado"


class TestMudarReceberEmailsController:
    def test_mudar_receber_emails_sucesso(
        self, client, cargo_padrao, atuacao_padrao, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        res = client.post(
            "/funcionarios",
            json={
                "nome": "Func Emails",
                "email": "emails@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        func_id = res.json()["funcionario_id"]

        response = client.patch(
            f"/funcionarios/{func_id}/receber-emails",
            json={"receber_emails": False},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["receber_emails"] is False

    def test_mudar_receber_emails_funcionario_inexistente_retorna_400(
        self, client, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.patch(
            "/funcionarios/9999/receber-emails",
            json={"receber_emails": False},
            headers=headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário não encontrado"


class TestEditarDadosController:
    def test_editar_dados_sem_token_retorna_erro(self, client):
        response = client.patch("/funcionarios", json={"nome": "Novo Nome"})
        assert response.status_code == 401

    def test_editar_dados_com_token_invalido_retorna_erro(self, client):
        response = client.patch(
            "/funcionarios",
            json={"nome": "Novo Nome"},
            headers={"Authorization": "Bearer token-invalido"},
        )
        assert response.status_code == 401

    def test_editar_dados_retorna_funcionario_atualizado(
        self, client, cargo_padrao, atuacao_padrao, token_acesso, token_admin
    ):
        headers_admin = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": "Funcionario Teste",
                "email": "funcionario.editar@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers_admin,
        )
        assert response.status_code == 201
        funcionario_id = response.json()["funcionario_id"]

        token = token_acesso(funcionario_id, "funcionario.editar@test.com")
        response = client.patch(
            "/funcionarios",
            json={"nome": "Nome Atualizado", "uf_oab": "SP", "numero_oab": "12345"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["nome"] == "Nome Atualizado"
        assert response.json()["uf_oab"] == "SP"
        assert response.json()["numero_oab"] == "12345"
        assert response.json()["email"] == "funcionario.editar@test.com"
        assert response.json()["funcionario_id"] == funcionario_id

    def test_editar_dados_funcionario_inexistente_retorna_erro(self, client, token_acesso):
        token = token_acesso(999)
        response = client.patch(
            "/funcionarios",
            json={"nome": "Novo Nome"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_editar_dados_erro_service_retorna_400(
        self, client, cargo_padrao, atuacao_padrao, token_acesso, token_admin
    ):
        headers_admin = {"Authorization": f"Bearer {token_admin}"}
        res = client.post(
            "/funcionarios",
            json={
                "nome": "Func Teste",
                "email": "func.erro@test.com",
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers_admin,
        )
        func_id = res.json()["funcionario_id"]
        token = token_acesso(func_id, "func.erro@test.com")

        with patch(
            "app.funcionario.controller.FuncionarioService.editar_dados",
            side_effect=ValueError("Erro ao editar"),
        ):
            response = client.patch(
                "/funcionarios",
                json={"nome": "Novo Nome"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 400
            assert response.json()["detail"] == "Erro ao editar"


class TestApagarFuncionarioController:
    @pytest.mark.parametrize(
        "nome,email",
        [
            ("Ana Beatriz Souza", "ana.souza@test.com"),
            ("Carlos Eduardo Lima", "carlos.lima@test.com"),
            ("Patrícia Almeida", "patricia.almeida@test.com"),
            ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
            ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
        ],
    )
    def test_apagar_funcionario_retorna_sucesso(
        self, client, cargo_padrao, atuacao_padrao, nome, email, token_admin
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.post(
            "/funcionarios",
            json={
                "nome": nome,
                "email": email,
                "cargo_id": cargo_padrao.cargo_id,
                "atuacao_id": atuacao_padrao.atuacao_id,
            },
            headers=headers,
        )
        assert response.status_code == 201

        funcionario_id = response.json()["funcionario_id"]
        response = client.delete(f"/funcionarios/{funcionario_id}", headers=headers)
        assert response.status_code == 204
        assert response.content == b""

    def test_apagar_funcionario_nao_encontrado_retorna_erro(self, client, token_admin):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.delete("/funcionarios/999", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário não encontrado"

    def test_apagar_funcionario_inexistente_retorna_400(self, client, token_admin):
        headers = {"Authorization": f"Bearer {token_admin}"}
        response = client.delete("/funcionarios/9999", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Funcionário não encontrado"


@pytest.fixture
def cargo_padrao(db_session):
    cargo = Cargo(nome_cargo="Advogado")
    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)
    return cargo


@pytest.mark.parametrize(
    "nome,email",
    [
        ("Ana Beatriz Souza", "ana.souza@test.com"),
        ("Carlos Eduardo Lima", "carlos.lima@test.com"),
        ("Patrícia Almeida", "patricia.almeida@test.com"),
        ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
        ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
    ],
)
def test_criar_funcionario(db_session, cargo_padrao, nome, email):
    repository = FuncionarioRepository(db_session)
    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome=nome,
        email=email,
        cargo_id=cargo_padrao.cargo_id,
    )

    criacao = repository.criar(funcionario)

    assert criacao.funcionario_id is not None
    assert criacao.nome == nome
    assert criacao.email == email
    assert criacao.cargo_id == cargo_padrao.cargo_id
    assert criacao.senha_hash is None
    assert criacao.uf_oab is None
    assert criacao.numero_oab is None
    assert criacao.status == StatusFuncionario.PENDENTE
    assert criacao.exibicao_institucional is False


def test_obter_todos_funcionarios(db_session, cargo_padrao):
    repository = FuncionarioRepository(db_session)
    funcionario1 = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Ana Beatriz Souza",
        email="ana.souza@test.com",
        cargo_id=cargo_padrao.cargo_id,
    )
    funcionario2 = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Outro Usuário",
        email="outro.usuario@test.com",
        cargo_id=cargo_padrao.cargo_id,
    )

    repository.criar(funcionario1)
    repository.criar(funcionario2)

    todos = repository.buscar_todos()

    assert len(todos) == 2
    assert todos[0].nome == "Ana Beatriz Souza"
    assert todos[0].email == "ana.souza@test.com"
    assert todos[1].nome == "Outro Usuário"
    assert todos[1].email == "outro.usuario@test.com"


def test_buscar_por_id(db_session, cargo_padrao):
    repository = FuncionarioRepository(db_session)
    funcionario1 = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Ana Beatriz Souza",
        email="ana.souza@test.com",
        cargo_id=cargo_padrao.cargo_id,
    )
    funcionario2 = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Outro Usuário",
        email="outro.usuario@test.com",
        cargo_id=cargo_padrao.cargo_id,
    )

    criacao1 = repository.criar(funcionario1)
    criacao2 = repository.criar(funcionario2)
    encontrado1 = repository.buscar_por_id(criacao1.funcionario_id)
    encontrado2 = repository.buscar_por_id(criacao2.funcionario_id)

    assert encontrado1 is not None
    assert encontrado1.nome == "Ana Beatriz Souza"
    assert encontrado1.email == "ana.souza@test.com"
    assert encontrado2 is not None
    assert encontrado2.nome == "Outro Usuário"
    assert encontrado2.email == "outro.usuario@test.com"


def test_buscar_por_email(db_session, cargo_padrao):
    repository = FuncionarioRepository(db_session)
    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Ana Beatriz Souza",
        email="ana.souza@test.com",
        cargo_id=cargo_padrao.cargo_id,
    )

    criacao = repository.criar(funcionario)
    encontrado = repository.buscar_por_email(criacao.email)

    assert encontrado is not None
    assert encontrado.nome == "Ana Beatriz Souza"
    assert encontrado.email == "ana.souza@test.com"


def test_atualizar_funcionario(db_session, cargo_padrao):
    repository = FuncionarioRepository(db_session)
    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Ana Beatriz Souza",
        email="ana.souza@test.com",
        cargo_id=cargo_padrao.cargo_id,
    )

    criacao = repository.criar(funcionario)

    criacao.nome = "Ana Beatriz Souza Updated"
    criacao.email = "ana.souza_updated@test.com"

    atualizacao = repository.atualizar(criacao)

    assert atualizacao is not None
    assert atualizacao.nome == "Ana Beatriz Souza Updated"
    assert atualizacao.email == "ana.souza_updated@test.com"


def test_apagar_funcionario(db_session, cargo_padrao):
    repository = FuncionarioRepository(db_session)
    funcionario1 = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Ana Beatriz Souza",
        email="ana.souza@test.com",
        cargo_id=cargo_padrao.cargo_id,
    )
    funcionario2 = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Outro Usuário",
        email="outro.usuario@test.com",
        cargo_id=cargo_padrao.cargo_id,
    )

    funcionario_a_deletar = repository.criar(funcionario1)
    repository.criar(funcionario2)
    busca = repository.buscar_todos()

    assert len(busca) == 2
    assert busca[0].nome == "Ana Beatriz Souza"
    assert busca[1].nome == "Outro Usuário"

    repository.deletar(funcionario_a_deletar)

    assert repository.buscar_por_id(busca[0].funcionario_id) is None
    assert repository.buscar_por_id(busca[1].funcionario_id) is not None
    assert len(repository.buscar_todos()) == 1
    assert repository.buscar_todos()[0].nome == "Outro Usuário"


def test_criar_funcionario_com_email_duplicado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_email.return_value = Funcionario(
        nome="Outro Usuário",
        email="ana.souza@test.com",
        cargo_id=1,
    )

    with pytest.raises(ValueError, match="Email já cadastrado"):
        service.criar_funcionario(
            FuncionarioCreate(
                nome="Ana Beatriz Souza", email="ana.souza@test.com", cargo_id=1, atuacao_id=1
            )
        )


@pytest.mark.parametrize(
    "nome,email",
    [
        ("Ana Beatriz Souza", "ana.souza@test.com"),
        ("Carlos Eduardo Lima", "carlos.lima@test.com"),
        ("Patrícia Almeida", "patricia.almeida@test.com"),
        ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
        ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
    ],
)
def test_criar_funcionario_com_email_unico(nome, email):
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)

    service.cargo_repository = MagicMock(spec=CargoRepository)
    service.cargo_repository.buscar_por_id.return_value = Cargo(cargo_id=1, nome_cargo="Advogado")
    service.atuacao_repository = MagicMock(spec=AtuacaoRepository)
    service.atuacao_repository.buscar_por_id.return_value = Atuacao(atuacao_id=1)
    service.arquivo_repository = MagicMock(spec=ArquivoRepository)
    service.arquivo_repository.obter_padrao.return_value = Arquivo(arquivo_id=7)

    service.repository.buscar_por_email.return_value = None
    service.repository.criar.return_value = Funcionario(
        nome=nome,
        email=email.lower(),
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.PENDENTE,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )

    funcionario = service.criar_funcionario(
        FuncionarioCreate(nome=nome, email=email, cargo_id=1, atuacao_id=1)
    )

    assert isinstance(funcionario, Funcionario)
    assert funcionario is not None
    assert funcionario.nome == nome
    assert funcionario.email == email.lower()
    assert funcionario.cargo_id == 1
    assert funcionario.status == StatusFuncionario.PENDENTE
    novo = service.repository.criar.call_args.args[0]
    assert (novo.atuacao_id, novo.foto_perfil) == (1, 7)


def test_criar_funcionario_com_atuacao_inexistente_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_email.return_value = None
    service.cargo_repository = MagicMock(spec=CargoRepository)
    service.cargo_repository.buscar_por_id.return_value = Cargo(cargo_id=1, nome_cargo="Advogado")
    service.atuacao_repository = MagicMock(spec=AtuacaoRepository)
    service.atuacao_repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Área de atuação não encontrada"):
        service.criar_funcionario(
            FuncionarioCreate(nome="Ana", email="ana@test.com", cargo_id=1, atuacao_id=99)
        )
    service.repository.criar.assert_not_called()


def test_buscar_todos_retorna_lista_de_funcionarios():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_todos.return_value = [
        Funcionario(
            nome="Ana Beatriz Souza",
            email="ana.souza@test.com",
            funcionario_id=1,
            cargo_id=1,
            status=StatusFuncionario.PENDENTE,
            uf_oab=None,
            numero_oab=None,
            exibicao_institucional=False,
        ),
        Funcionario(
            nome="Outro Usuário",
            email="outro.usuario@test.com",
            funcionario_id=2,
            cargo_id=1,
            status=StatusFuncionario.PENDENTE,
            uf_oab=None,
            numero_oab=None,
            exibicao_institucional=False,
        ),
    ]

    funcionarios = service.buscar_todos()

    assert isinstance(funcionarios, list)
    assert len(funcionarios) == 2
    assert funcionarios[0].nome == "Ana Beatriz Souza"
    assert funcionarios[0].email == "ana.souza@test.com"
    assert funcionarios[1].nome == "Outro Usuário"
    assert funcionarios[1].email == "outro.usuario@test.com"
    assert isinstance(funcionarios[0], Funcionario)
    assert isinstance(funcionarios[1], Funcionario)


def test_primeiro_acesso_funcionario_nao_encontrado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.primeiro_acesso(1, FuncionarioPrimeiroAcesso(token="token-teste", senha="test123"))


def test_primeiro_acesso_funcionario_com_conta_pendente_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario

    with pytest.raises(ValueError, match="Funcionário já teve a conta ativada"):
        service.primeiro_acesso(1, FuncionarioPrimeiroAcesso(token="token-teste", senha="test123"))


def test_primeiro_acesso_funcionario_com_sucesso():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Ana Beatriz Souza",
        email="ana.souza@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.PENDENTE,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario
    service.repository.atualizar.return_value = funcionario

    dados_acesso = FuncionarioPrimeiroAcesso(
        token="token-teste",
        senha="test123",
        nome="Ana Beatriz Souza",
        uf_oab="SP",
        numero_oab="12345",
    )
    funcionario_atualizado = service.primeiro_acesso(1, dados_acesso)

    assert isinstance(funcionario_atualizado, Funcionario)
    assert funcionario_atualizado.nome == "Ana Beatriz Souza"
    assert funcionario_atualizado.email == "ana.souza@test.com"
    assert funcionario_atualizado.uf_oab == "SP"
    assert funcionario_atualizado.numero_oab == "12345"
    assert funcionario_atualizado.status == StatusFuncionario.ATIVO


def test_mudar_cargo_funcionario_nao_encontrado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.mudar_cargo(1, 2)


def test_mudar_cargo_com_cargo_inexistente_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )
    service.repository.buscar_por_id.return_value = funcionario

    service.cargo_repository = MagicMock(spec=CargoRepository)
    service.cargo_repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Cargo não encontrado"):
        service.mudar_cargo(1, 999)


def test_mudar_cargo_com_sucesso():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )
    service.repository.buscar_por_id.return_value = funcionario
    service.repository.atualizar.return_value = funcionario

    service.cargo_repository = MagicMock(spec=CargoRepository)
    service.cargo_repository.buscar_por_id.return_value = Cargo(cargo_id=2, nome_cargo="Sócio")

    funcionario_atualizado = service.mudar_cargo(1, 2)

    assert isinstance(funcionario_atualizado, Funcionario)
    assert funcionario_atualizado.cargo_id == 2


def test_editar_dados_funcionario_nao_encontrado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.editar_dados(1, FuncionarioUpdate(nome="Novo Nome"))


def test_editar_dados_atualiza_campos_permitidos():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )
    service.repository.buscar_por_id.return_value = funcionario
    service.repository.atualizar.return_value = funcionario

    dados = FuncionarioUpdate(
        nome="Nome Atualizado", senha="nova-senha123", uf_oab="SP", numero_oab="12345"
    )
    funcionario_atualizado = service.editar_dados(1, dados)

    assert funcionario_atualizado.nome == "Nome Atualizado"
    assert funcionario_atualizado.uf_oab == "SP"
    assert funcionario_atualizado.numero_oab == "12345"
    assert funcionario_atualizado.senha_hash is not None
    assert funcionario_atualizado.senha_hash != "nova-senha123"
    assert funcionario_atualizado.email == "usuario.teste@test.com"
    assert funcionario_atualizado.status == StatusFuncionario.ATIVO


def test_editar_dados_sem_campos_nao_altera_dados_sensiveis():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )
    service.repository.buscar_por_id.return_value = funcionario
    service.repository.atualizar.return_value = funcionario

    funcionario_atualizado = service.editar_dados(1, FuncionarioUpdate())

    assert funcionario_atualizado.nome == "Usuário Teste"
    assert funcionario_atualizado.email == "usuario.teste@test.com"
    assert funcionario_atualizado.status == StatusFuncionario.ATIVO
    assert funcionario_atualizado.cargo_id == 1


def test_mudar_acesso_funcionario_nao_encontrado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.mudar_acesso(1)


def test_mudar_acesso_funcionario_com_conta_pendente_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.PENDENTE,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario

    with pytest.raises(ValueError, match="Funcionário ainda não ativou a conta"):
        service.mudar_acesso(1)


def test_mudar_acesso_funcionario_com_conta_ativa_para_inativa():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario

    service.repository.atualizar.return_value = funcionario

    funcionario_atualizado = service.mudar_acesso(1)

    assert isinstance(funcionario_atualizado, Funcionario)
    assert funcionario_atualizado.status == StatusFuncionario.INATIVO


def test_mudar_acesso_funcionario_com_conta_inativa_para_ativa():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.INATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario

    service.repository.atualizar.return_value = funcionario

    funcionario_atualizado = service.mudar_acesso(1)

    assert isinstance(funcionario_atualizado, Funcionario)
    assert funcionario_atualizado.status == StatusFuncionario.ATIVO


def test_apagar_funcionario_nao_encontrado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.apagar_funcionario(1)


def test_apagar_funcionario_retorna_sucesso():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        cargo_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicao_institucional=False,
    )
    service.repository.buscar_por_id.return_value = funcionario

    resultado = service.apagar_funcionario(1)

    assert resultado is None
    service.repository.buscar_por_id.assert_called_once_with(1)
    service.repository.deletar.assert_called_once_with(funcionario)


def test_construtor_cria_repository_com_a_sessao_informada(db_session):
    service = FuncionarioService(db_session)

    assert isinstance(service.repository, FuncionarioRepository)
    assert service.repository.db is db_session


def test_buscar_visiveis_institucional_retorna_lista():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_visiveis_institucional.return_value = [
        Funcionario(funcionario_id=1, nome="Visivel", exibicao_institucional=True)
    ]
    resultado = service.buscar_visiveis_institucional()
    assert len(resultado) == 1
    assert resultado[0].nome == "Visivel"


def test_mudar_exibicao_institucional_sucesso():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(funcionario_id=1, nome="Teste", exibicao_institucional=False)
    service.repository.buscar_por_id.return_value = funcionario
    service.repository.atualizar.return_value = funcionario

    resultado = service.mudar_exibicao_institucional(1, True)
    assert resultado.exibicao_institucional is True
    service.repository.atualizar.assert_called_once_with(funcionario)


def test_mudar_exibicao_institucional_funcionario_nao_encontrado_lanca_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.mudar_exibicao_institucional(999, True)


def test_mudar_receber_emails_sucesso():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(funcionario_id=1, nome="Teste", receber_emails=True)
    service.repository.buscar_por_id.return_value = funcionario
    service.repository.atualizar.return_value = funcionario

    resultado = service.mudar_receber_emails(1, False)
    assert resultado.receber_emails is False
    service.repository.atualizar.assert_called_once_with(funcionario)


def test_mudar_receber_emails_funcionario_nao_encontrado_lanca_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.mudar_receber_emails(999, False)
