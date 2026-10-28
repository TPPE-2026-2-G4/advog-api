from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.atividade.model import Atividade
from app.atividade.schema import AtividadeFilter
from app.atividade.service import AtividadeService
from app.cargo.model import Cargo
from app.etapa_kanban.model import EtapaKanban
from app.funcionario.model import Funcionario


@pytest.mark.parametrize(
    ("permissoes", "escopo", "funcionario_id"),
    [
        (None, "usuario", 7),
        ({}, "usuario", 7),
        ({"gerenciar_equipe": False}, "usuario", 7),
        ({"visualizar_equipe": True}, "usuario", 7),
        ({"gerenciar_equipe": True}, "escritorio", None),
    ],
)
def test_kanban_determina_escopo_e_agrupa_cartoes(permissoes, escopo, funcionario_id):
    service = AtividadeService(MagicMock())
    service.repository = MagicMock()
    service.repository.buscar_etapas.return_value = [
        EtapaKanban(etapa_id=2, nome="Em Execução", ordem=1),
        EtapaKanban(etapa_id=1, nome="Backlog", ordem=2),
    ]
    service.repository.buscar_atividades.return_value = [
        Atividade(
            atividade_id=3,
            titulo="Atividade",
            data_prazo=datetime(2026, 10, 30),
            etapa_id=1,
            processo_id=None,
        )
    ]
    service.repository.buscar_responsaveis.return_value = [(3, 7, "Responsável")]
    funcionario = Funcionario(
        atuacao_id=1, foto_perfil=1, funcionario_id=7, cargo=Cargo(permissao=permissoes)
    )

    resultado = service.visualizar_kanban(funcionario)

    assert resultado.escopo == escopo
    assert [etapa.etapa_id for etapa in resultado.etapas] == [2, 1]
    assert resultado.etapas[0].atividades == []
    cartao = resultado.etapas[1].atividades[0]
    assert cartao.atividade_id == 3
    assert cartao.responsaveis[0].model_dump() == {"funcionario_id": 7, "nome": "Responsável"}
    service.repository.buscar_atividades.assert_called_once_with(funcionario_id=funcionario_id)
    service.repository.buscar_responsaveis.assert_called_once_with([3])


@pytest.mark.parametrize(
    "contagens, progresso",
    [
        ((1, 1, 3, 3), 12.5),
        ((1, 0, 0, 0), 100.0),
        ((0, 0, 0, 0), 0.0),
        ((1, 1, 1, 0), 33.33),
    ],
)
def test_produtividade_calcula_progresso_e_usa_dia_local(contagens, progresso):
    from zoneinfo import ZoneInfo

    service = AtividadeService(MagicMock())
    totais = dict(
        zip(("finalizadas", "a_fazer", "em_andamento", "atrasadas"), contagens, strict=True)
    )
    service.repository.buscar_produtividade_equipe = MagicMock(
        return_value=[{"funcionario_id": 7, "nome": "Responsável", **totais}]
    )
    with patch("app.atividade.service.datetime", wraps=datetime) as relogio:
        relogio.now.return_value = datetime(2026, 10, 22, 23, 30)
        resultado = service.visualizar_produtividade_equipe()

    relogio.now.assert_called_once_with(ZoneInfo("America/Sao_Paulo"))
    service.repository.buscar_produtividade_equipe.assert_called_once_with(datetime(2026, 10, 22))
    assert resultado[0].model_dump() == {
        "funcionario_id": 7,
        "nome": "Responsável",
        **totais,
        "progresso": progresso,
    }


def test_produtividade_retorna_equipe_vazia():
    service = AtividadeService(MagicMock())
    service.repository.buscar_produtividade_equipe = MagicMock(return_value=[])
    assert service.visualizar_produtividade_equipe() == []


@pytest.mark.parametrize(
    ("termo_busca", "qtd_esperada", "titulo_esperado"),
    [
        ("Elaborar Petição", 1, "Elaborar Petição Inicial"),
        ("Revisão", 1, "Revisão de Contrato"),
        ("InexistenteNoBanco", 0, None),
    ],
)
def test_buscar_atividades_com_filtros(
    db_session, atividades_para_filtro, termo_busca, qtd_esperada, titulo_esperado
):
    service = AtividadeService(db_session)

    filtro = AtividadeFilter.model_validate({"titulo": termo_busca})
    resultado = service.buscar_atividades(filtro)

    assert len(resultado) == qtd_esperada
    if qtd_esperada > 0:
        assert resultado[0].titulo == titulo_esperado


@pytest.mark.parametrize(
    ("apenas_minhas", "funcionario_id_filtro", "funcionario_id_esperado"),
    [
        (True, 99, 42),
        (False, 99, 99),
    ],
)
def test_buscar_atividades_trata_funcionario_id_conforme_apenas_minhas(
    apenas_minhas, funcionario_id_filtro, funcionario_id_esperado
):
    service = AtividadeService(MagicMock())
    service.repository = MagicMock()
    service.repository.buscar_por_filtros.return_value = []

    usuario = Funcionario(atuacao_id=1, foto_perfil=1, funcionario_id=42)
    filtro = AtividadeFilter.model_validate(
        {"apenas_minhas": apenas_minhas, "funcionario_id": funcionario_id_filtro}
    )

    service.buscar_atividades(filtro, usuario=usuario)

    _, kwargs = service.repository.buscar_por_filtros.call_args
    assert kwargs["funcionario_id"] == funcionario_id_esperado
