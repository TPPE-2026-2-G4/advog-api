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


def test_get_institucional_publico_sucesso(client, seed_institucional_db):
    response = client.get("/institucional")
    assert response.status_code == 200
    assert response.json()["nomeEscritorio"] == "Escritório Modelo"


def test_put_institucional_sem_token_retorna_401(client):
    response = client.put("/institucional", json={"nomeEscritorio": "Novo"})
    assert response.status_code == 401


def test_put_institucional_sem_permissao_retorna_403(client, token_sem_permissao):
    headers = {"Authorization": f"Bearer {token_sem_permissao}"}
    response = client.put("/institucional", json={"nomeEscritorio": "Novo"}, headers=headers)
    assert response.status_code == 403


def test_put_institucional_com_token_admin_sucesso(client, seed_institucional_db, token_admin):
    headers = {"Authorization": f"Bearer {token_admin}"}
    payload = {"nomeEscritorio": "Escritório Atualizado"}

    response = client.put("/institucional", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["nomeEscritorio"] == "Escritório Atualizado"


@patch("app.services.institucional.salvar_arquivo")
@patch("app.services.institucional.obter_url_publica")
def test_post_upload_logo_sucesso(
    mock_url, mock_salvar, client, seed_institucional_db, token_admin
):
    mock_salvar.return_value = "logotipos/logo_teste.png"
    mock_url.return_value = "http://localhost:9000/institucional/logotipos/logo_teste.png"

    headers = {"Authorization": f"Bearer {token_admin}"}
    files = {
        "file": (
            "logo.png",
            io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"),
            "image/png",
        )
    }

    response = client.post("/institucional/upload/logo", files=files, headers=headers)
    assert response.status_code == 200
    assert response.json()["url"] == "http://localhost:9000/institucional/logotipos/logo_teste.png"


def test_post_upload_tipo_invalido_retorna_400(client, token_admin):
    headers = {"Authorization": f"Bearer {token_admin}"}
    files = {"file": ("teste.txt", io.BytesIO(b"conteudo"), "text/plain")}

    response = client.post("/institucional/upload/invalido", files=files, headers=headers)
    assert response.status_code == 400
