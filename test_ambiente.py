import importlib.util
import os

import pytest
from sqlalchemy import inspect, text

from app.config.database import Base
from main import app

TABELAS_DO_DLD = {
    "arquivos",
    "atividades",
    "atividades_funcionarios",
    "atuacoes",
    "cargos",
    "categoria_lancamentos",
    "clientes",
    "clientes_arquivos",
    "etapas_cliente",
    "etapas_kanban",
    "funcionarios",
    "institucional",
    "lancamentos",
    "notificacoes",
    "processos",
    "processos_arquivos",
    "processos_movimentacoes",
    "tokens_recuperacao_senha",
}


@pytest.mark.parametrize(
    "modulo",
    [
        "apscheduler",
        "bcrypt",
        "boto3",
        "defusedxml",
        "dotenv",
        "fastapi",
        "fastapi_mail",
        "filetype",
        "httpx",
        "jwt",
        "openpyxl",
        "passlib",
        "PIL",
        "psycopg2",
        "reportlab",
        "slowapi",
        "sqlalchemy",
    ],
)
def test_dependencia_esta_instalada(modulo):
    assert importlib.util.find_spec(modulo) is not None, f"Dependência '{modulo}' não instalada"


@pytest.mark.parametrize(
    "variavel",
    [
        "S3_ENDPOINT",
        "S3_PUBLIC_URL",
        "S3_BUCKET_PUBLICO",
        "S3_BUCKET_PRIVADO",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ],
)
def test_variavel_de_ambiente_obrigatoria_esta_definida(variavel):
    assert os.getenv(variavel), f"Variável '{variavel}' não definida (veja o .env.example)"


def test_aplicacao_responde_na_raiz(client):
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "Bem vindo" in resposta.json()["message"]


def test_documentacao_da_api_esta_disponivel(client):
    assert client.get("/docs").status_code == 200

    esquema = client.get("/openapi.json")

    assert esquema.status_code == 200
    assert esquema.json()["info"]["title"] == app.title


def test_banco_responde_a_consultas(db_session):
    assert db_session.execute(text("SELECT 1")).scalar() == 1


def test_banco_cria_todas_as_tabelas_do_dld(db_session):
    tabelas_no_banco = set(inspect(db_session.get_bind()).get_table_names())

    assert set(Base.metadata.tables) == TABELAS_DO_DLD
    assert tabelas_no_banco == TABELAS_DO_DLD


def test_endpoints_de_health_estao_registrados(client):
    resposta_liveness = client.get("/health")
    assert resposta_liveness.status_code == 200
    assert resposta_liveness.json() == {"status": "ok", "service": "advog-api"}


def test_cors_origins_e_frontend_url_desacoplados():
    from main import CORS_ORIGINS

    assert isinstance(CORS_ORIGINS, list)
    assert len(CORS_ORIGINS) > 0
