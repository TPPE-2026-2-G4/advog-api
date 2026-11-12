"""Configuração de alertas do escritório (Ajustes): antecedência dos prazos e processo crítico."""

import pytest

from app.cargo.model import Cargo
from app.funcionario.model import Funcionario, StatusFuncionario


def _usuario(db, arquivo, nome, permissao):
    cargo = Cargo(nome_cargo=f"Cargo {nome}", permissao=permissao)
    db.add(cargo)
    db.commit()
    funcionario = Funcionario(
        nome=nome,
        email=f"{nome.lower()}@teste.com",
        status=StatusFuncionario.ATIVO,
        cargo_id=cargo.cargo_id,
        foto_perfil=arquivo.arquivo_id,
    )
    db.add(funcionario)
    db.commit()
    return funcionario


@pytest.fixture
def cabecalhos(db_session, arquivo_padrao, token_acesso):
    def para(funcionario):
        return {
            "Authorization": f"Bearer {token_acesso(funcionario.funcionario_id, funcionario.email)}"
        }

    gestor = _usuario(db_session, arquivo_padrao, "Gestor", {"configuracoes_sistema": True})
    comum = _usuario(db_session, arquivo_padrao, "Comum", {})
    return {"gestor": para(gestor), "comum": para(comum)}


def test_valores_padrao_sem_cadastro_institucional(client, cabecalhos):
    resposta = client.get("/institucional/alertas", headers=cabecalhos["comum"])

    assert resposta.status_code == 200
    assert resposta.json() == {"dias_prazo_proximo": 15, "dias_processo_critico": 15}


def test_gestor_altera_e_todos_enxergam(client, cabecalhos, institucional_padrao, db_session):
    resposta = client.patch(
        "/institucional/alertas",
        json={"dias_prazo_proximo": 30, "dias_processo_critico": 45},
        headers=cabecalhos["gestor"],
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"dias_prazo_proximo": 30, "dias_processo_critico": 45}
    db_session.refresh(institucional_padrao)
    assert institucional_padrao.dias_prazo_proximo == 30
    lido_por_usuario_comum = client.get("/institucional/alertas", headers=cabecalhos["comum"])
    assert lido_por_usuario_comum.json() == {"dias_prazo_proximo": 30, "dias_processo_critico": 45}


def test_atualiza_so_o_campo_enviado(client, cabecalhos, institucional_padrao):
    resposta = client.patch(
        "/institucional/alertas", json={"dias_processo_critico": 7}, headers=cabecalhos["gestor"]
    )

    assert resposta.json() == {"dias_prazo_proximo": 15, "dias_processo_critico": 7}


def test_usuario_sem_permissao_nao_altera(client, cabecalhos, institucional_padrao):
    resposta = client.patch(
        "/institucional/alertas", json={"dias_prazo_proximo": 7}, headers=cabecalhos["comum"]
    )

    assert resposta.status_code == 403


def test_alterar_sem_cadastro_institucional_retorna_404(client, cabecalhos):
    resposta = client.patch(
        "/institucional/alertas", json={"dias_prazo_proximo": 7}, headers=cabecalhos["gestor"]
    )

    assert resposta.status_code == 404


@pytest.mark.parametrize(
    "corpo",
    [
        {"dias_prazo_proximo": 10},
        {"dias_prazo_proximo": 0},
        {"dias_processo_critico": 0},
        {"dias_processo_critico": 366},
        {"dias_processo_critico": "muitos"},
        {"outro_campo": 1},
    ],
)
def test_rejeita_valores_invalidos(client, cabecalhos, institucional_padrao, corpo):
    resposta = client.patch("/institucional/alertas", json=corpo, headers=cabecalhos["gestor"])

    assert resposta.status_code == 422


def test_leitura_e_escrita_exigem_login(client, institucional_padrao):
    assert client.get("/institucional/alertas").status_code == 401
    assert client.patch("/institucional/alertas", json={"dias_prazo_proximo": 7}).status_code == 401
