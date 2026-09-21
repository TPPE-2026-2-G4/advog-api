import io
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.cargo import Cargo
from app.models.funcionario import Funcionario, StatusFuncionario
from app.models.institucional import Institucional
from app.utils.seguranca import criar_token_acesso


@pytest.fixture
def seed_institucional_db(db_session: Session):
    config = Institucional(
        institucional_id=1,
        nome_escritorio="Escritório Modelo",
        cor_primaria="#1B2A4A",
        cor_secundaria="#B79A63",
    )
    db_session.add(config)
    db_session.commit()
    return config


@pytest.fixture
def token_admin(db_session: Session):
    cargo = Cargo(
        nome_cargo="Administrador",
        permissao={"configuracoes_sistema": True},
    )
    db_session.add(cargo)
    db_session.commit()

    admin = Funcionario(
        nome="Admin Teste",
        email="admin@teste.com",
        cargo_id=cargo.cargo_id,
        status=StatusFuncionario.ATIVO,
    )
    db_session.add(admin)
    db_session.commit()

    return criar_token_acesso({"sub": str(admin.funcionario_id), "email": admin.email})


@pytest.fixture
def token_sem_permissao(db_session: Session):
    cargo = Cargo(
        nome_cargo="Assistente",
        permissao={"configuracoes_sistema": False},
    )
    db_session.add(cargo)
    db_session.commit()

    user = Funcionario(
        nome="User Comum",
        email="user@teste.com",
        cargo_id=cargo.cargo_id,
        status=StatusFuncionario.ATIVO,
    )
    db_session.add(user)
    db_session.commit()

    return criar_token_acesso({"sub": str(user.funcionario_id), "email": user.email})


def _gerar_upload_file(filename: str = "imagem.png"):
    return {
        "file": (
            filename,
            io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"),
            "image/png",
        )
    }


class TestObterInstitucionalController:
    def test_obter_configuracoes_publicas_sucesso(self, client, seed_institucional_db):
        response = client.get("/institucional")

        assert response.status_code == 200
        assert response.json()["nomeEscritorio"] == "Escritório Modelo"

    def test_obter_equipe_publica_retorna_apenas_funcionarios_visiveis(self, client, db_session):
        cargo = Cargo(nome_cargo="Advogado", permissao={})
        db_session.add(cargo)
        db_session.commit()

        f1 = Funcionario(
            nome="Dr. Alexandre",
            email="alexandre@teste.com",
            cargo_id=cargo.cargo_id,
            status=StatusFuncionario.ATIVO,
            exibicao_institucional=True,
        )
        f2 = Funcionario(
            nome="Dra. Ana",
            email="ana@teste.com",
            cargo_id=cargo.cargo_id,
            status=StatusFuncionario.ATIVO,
            exibicao_institucional=False,
        )
        f3 = Funcionario(
            nome="Dr. Pedro Inativo",
            email="pedro@teste.com",
            cargo_id=cargo.cargo_id,
            status=StatusFuncionario.INATIVO,
            exibicao_institucional=True,
        )
        db_session.add_all([f1, f2, f3])
        db_session.commit()

        response = client.get("/institucional/equipe")

        assert response.status_code == 200
        dados = response.json()
        assert len(dados) == 1
        assert dados[0]["nome"] == "Dr. Alexandre"
        assert dados[0]["exibicaoInstitucional"] is True


class TestAtualizarInstitucionalController:
    def test_atualizar_configuracoes_sem_token_retorna_401(self, client):
        response = client.put("/institucional", json={"nomeEscritorio": "Novo"})

        assert response.status_code == 401

    def test_atualizar_configuracoes_sem_permissao_retorna_403(self, client, token_sem_permissao):
        headers = {"Authorization": f"Bearer {token_sem_permissao}"}

        response = client.put("/institucional", json={"nomeEscritorio": "Novo"}, headers=headers)

        assert response.status_code == 403

    @pytest.mark.parametrize(
        "payload,campo_verificado,valor_esperado",
        [
            (
                {"nomeEscritorio": "Escritório Atualizado"},
                "nomeEscritorio",
                "Escritório Atualizado",
            ),
            (
                {
                    "sobreEscritorio": "Fundado em 2010...",
                    "textoAdicionalSobre": "Mais de 500 casos atendidos · 15 anos de atuação",
                },
                "sobreEscritorio",
                "Fundado em 2010...",
            ),
        ],
    )
    def test_atualizar_configuracoes_com_token_admin_sucesso(
        self,
        client,
        seed_institucional_db,
        token_admin,
        payload,
        campo_verificado,
        valor_esperado,
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}

        response = client.put("/institucional", json=payload, headers=headers)

        assert response.status_code == 200
        assert response.json()[campo_verificado] == valor_esperado


class TestUploadMidiaInstitucionalController:
    @pytest.mark.parametrize("tipo,pasta", [("logo", "logotipos"), ("sobre", "sobre")])
    @patch("app.services.institucional.salvar_arquivo")
    @patch("app.services.institucional.obter_url_publica")
    def test_upload_midia_sucesso(
        self,
        mock_url,
        mock_salvar,
        client,
        seed_institucional_db,
        token_admin,
        tipo,
        pasta,
    ):
        mock_salvar.return_value = f"{pasta}/imagem_teste.png"
        mock_url.return_value = f"http://localhost:9000/institucional/{pasta}/imagem_teste.png"

        headers = {"Authorization": f"Bearer {token_admin}"}
        files = _gerar_upload_file(f"{tipo}.png")

        response = client.post(f"/institucional/upload/{tipo}", files=files, headers=headers)

        assert response.status_code == 200
        assert (
            response.json()["url"]
            == f"http://localhost:9000/institucional/{pasta}/imagem_teste.png"
        )

    def test_upload_tipo_invalido_retorna_400(self, client, token_admin):
        headers = {"Authorization": f"Bearer {token_admin}"}
        files = {"file": ("teste.txt", io.BytesIO(b"conteudo"), "text/plain")}

        response = client.post("/institucional/upload/invalido", files=files, headers=headers)

        assert response.status_code == 400
