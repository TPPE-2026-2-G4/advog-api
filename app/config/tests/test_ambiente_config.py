import pytest

from app.config.ambiente import obter_environment


@pytest.fixture(autouse=True)
def limpar_variaveis(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RENDER", raising=False)


def test_sem_nenhuma_variavel_nao_e_producao():
    assert obter_environment() == ""


def test_environment_explicito_tem_prioridade_e_e_normalizado(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "  Production ")
    assert obter_environment() == "production"


def test_render_true_sem_environment_e_tratado_como_producao(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    assert obter_environment() == "production"

    monkeypatch.setenv("RENDER", " TRUE ")
    assert obter_environment() == "production"


def test_render_false_nao_e_producao(monkeypatch):
    monkeypatch.setenv("RENDER", "false")
    assert obter_environment() == ""


def test_environment_explicito_nao_e_sobrescrito_pelo_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert obter_environment() == "development"
