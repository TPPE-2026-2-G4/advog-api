from datetime import datetime

import pytest
from pydantic import ValidationError

from app.atividade.model import Atividade
from app.atividade.schema import AtividadeKanbanResponse, EtapaKanbanResponse, KanbanResponse
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
