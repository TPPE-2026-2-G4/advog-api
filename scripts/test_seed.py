import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from app.arquivo.model import Arquivo
from app.atividade.model import Atividade
from app.etapa_cliente.model import EtapaCliente
from app.etapa_kanban.model import EtapaKanban
from app.funcionario.model import Funcionario
from app.institucional.model import Institucional
from scripts.seed import ETAPAS_CLIENTE, ETAPAS_KANBAN, seed


@pytest.fixture()
def seed_com_banco_de_teste(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@advog.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-segura-123")
    with (
        patch("scripts.seed.engine", db_session.get_bind()),
        patch("scripts.seed.SessionLocal", return_value=db_session),
        patch("scripts.seed.garantir_bucket"),
        patch("scripts.seed.salvar_arquivo", return_value="sobre/default_sobre.jpg"),
    ):
        yield seed


@pytest.mark.parametrize("etapas_pre_existentes", [[], [2], [1, 2, 3, 4, 5]])
def test_seed_completa_etapas_de_cliente_sem_duplicar(
    seed_com_banco_de_teste, db_session, etapas_pre_existentes
):
    db_session.add_all(
        EtapaCliente(etapa_id=i, nome_etapa=f"Etapa {i}") for i in etapas_pre_existentes
    )
    db_session.commit()

    seed_com_banco_de_teste()
    seed_com_banco_de_teste()

    etapas = {e.etapa_id: e.nome_etapa for e in db_session.query(EtapaCliente)}
    esperado = dict(enumerate(ETAPAS_CLIENTE, start=1))
    esperado.update({i: f"Etapa {i}" for i in etapas_pre_existentes})
    assert etapas == esperado


def test_seed_cria_administrador_e_institucional_com_arquivos(seed_com_banco_de_teste, db_session):
    seed_com_banco_de_teste()
    seed_com_banco_de_teste()

    admin = db_session.query(Funcionario).one()
    institucional = db_session.query(Institucional).one()
    padrao = db_session.query(Arquivo).filter_by(bucket_link="").one()
    assert admin.foto_perfil == padrao.arquivo_id
    assert institucional.imagem_logotipo == institucional.banner_hero == padrao.arquivo_id
    assert institucional.link_imagem_sobre == "sobre/default_sobre.jpg"


@pytest.mark.parametrize("nome_existente", [None, "Backlog", "Personalizada"])
def test_seed_preserva_etapas_kanban_existentes_e_nao_duplica(
    seed_com_banco_de_teste, db_session, nome_existente
):
    if nome_existente is not None:
        db_session.add(EtapaKanban(nome=nome_existente, ordem=10))
        db_session.commit()

    seed_com_banco_de_teste()
    seed_com_banco_de_teste()

    etapas = {etapa.nome: etapa.ordem for etapa in db_session.query(EtapaKanban)}
    esperado = {nome: ordem for ordem, nome in enumerate(ETAPAS_KANBAN, start=1)}
    if nome_existente is not None:
        esperado[nome_existente] = 10
    assert etapas == esperado
    assert db_session.query(Atividade).count() == 0


def test_seed_roda_isolado_sem_depender_de_outros_modulos_carregados(tmp_path):
    codigo = (
        "from unittest.mock import patch\n"
        "import scripts.seed as seed\n"
        "with patch.object(seed, 'garantir_bucket'), patch.object(seed, 'salvar_arquivo', "
        "return_value='sobre/default_sobre.jpg'):\n"
        "    seed.seed()\n"
    )
    ambiente = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).parent.parent),
        "DATABASE_URL": f"sqlite:///{tmp_path / 'seed.sqlite'}",
        "ADMIN_EMAIL": "admin@advog.com",
        "ADMIN_PASSWORD": "senha-segura-123",
    }

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=tmp_path,
        env=ambiente,
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
