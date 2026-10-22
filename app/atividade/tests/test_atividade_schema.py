from datetime import datetime

import pytest
from pydantic import ValidationError

from app.atividade.model import Atividade
from app.atividade.schema import (
    AtividadeKanbanResponse,
    EtapaKanbanResponse,
    KanbanResponse,
    ProdutividadeResponse,
)
from app.etapa_kanban.model import EtapaKanban


@pytest.mark.parametrize("processo_id", [None, 12])
def test_cartao_serializa_somente_campos_de_visualizacao(processo_id):
    atividade = Atividade(
        atividade_id=1,
        titulo="Preparar defesa",
        descricao="Descrição detalhada",
        data_inicio=datetime(2026, 10, 1),
        data_prazo=datetime(2026, 10, 30, 15, 30),
        etapa_id=1,
        processo_id=processo_id,
    )

    cartao = AtividadeKanbanResponse.model_validate(atividade)

    assert cartao.model_dump(mode="json") == {
        "atividade_id": 1,
        "titulo": "Preparar defesa",
        "data_prazo": "2026-10-30T15:30:00",
        "processo_id": processo_id,
        "responsaveis": [],
    }


def test_etapas_vazias_possuem_listas_independentes():
    etapa = EtapaKanban(etapa_id=1, nome="Backlog", ordem=1)

    primeira = EtapaKanbanResponse.model_validate(etapa)
    segunda = EtapaKanbanResponse.model_validate(etapa)

    assert primeira.atividades == []
    assert primeira.atividades is not segunda.atividades


def test_kanban_rejeita_escopo_desconhecido():
    with pytest.raises(ValidationError):
        KanbanResponse.model_validate({"escopo": "todos", "etapas": []})


def test_produtividade_serializa_contrato():
    dados = {
        "funcionario_id": 7,
        "nome": "Responsável",
        "finalizadas": 1,
        "a_fazer": 1,
        "em_andamento": 3,
        "atrasadas": 3,
        "progresso": 12.5,
    }
    assert ProdutividadeResponse.model_validate(dados).model_dump(mode="json") == dados


@pytest.mark.parametrize(
    "campo",
    ["funcionario_id", "nome", "finalizadas", "a_fazer", "em_andamento", "atrasadas", "progresso"],
)
def test_produtividade_exige_campos_do_contrato(campo):
    dados = {
        "funcionario_id": 7,
        "nome": "Responsável",
        "finalizadas": 0,
        "a_fazer": 0,
        "em_andamento": 0,
        "atrasadas": 0,
        "progresso": 0.0,
    }
    del dados[campo]
    with pytest.raises(ValidationError):
        ProdutividadeResponse.model_validate(dados)
