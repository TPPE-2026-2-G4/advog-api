from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.atividade.model import Atividade
from app.atividade.schema import (
    AtividadeFilter,
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


@pytest.mark.parametrize(
    ("inputs", "esperados"),
    [
        (
            {},
            {
                "apenas_minhas": False,
                "atividade_id": None,
                "titulo": None,
                "descricao": None,
                "etapa_id": None,
                "processo_id": None,
                "funcionario_id": None,
                "prazo_inicio": None,
                "prazo_fim": None,
                "data_inicio_de": None,
                "data_inicio_ate": None,
                "realizada": None,
                "atrasada": None,
                "busca_textual": None,
            },
        ),
        (
            {
                "atividade_id": 10,
                "titulo": "Elaborar recurso",
                "descricao": "Recurso de apelação",
                "etapa_id": 2,
                "processo_id": 5,
                "funcionario_id": 7,
                "prazo_inicio": date(2026, 10, 1),
                "prazo_fim": date(2026, 10, 31),
                "data_inicio_de": date(2026, 10, 1),
                "data_inicio_ate": date(2026, 10, 15),
                "realizada": False,
                "atrasada": True,
                "apenas_minhas": True,
                "busca_textual": "recurso apelação",
            },
            {
                "atividade_id": 10,
                "titulo": "Elaborar recurso",
                "descricao": "Recurso de apelação",
                "etapa_id": 2,
                "processo_id": 5,
                "funcionario_id": 7,
                "prazo_inicio": date(2026, 10, 1),
                "prazo_fim": date(2026, 10, 31),
                "data_inicio_de": date(2026, 10, 1),
                "data_inicio_ate": date(2026, 10, 15),
                "realizada": False,
                "atrasada": True,
                "apenas_minhas": True,
                "busca_textual": "recurso apelação",
            },
        ),
    ],
)
def test_atividade_filter_instanciacao_e_valores(inputs, esperados):
    filtro = AtividadeFilter(**inputs)
    for campo, valor_esperado in esperados.items():
        assert getattr(filtro, campo) == valor_esperado


@pytest.mark.parametrize(
    ("dados_datas", "mensagem_erro"),
    [
        (
            {"prazo_inicio": date(2026, 10, 31), "prazo_fim": date(2026, 10, 1)},
            "prazo_inicio não pode ser posterior a prazo_fim",
        ),
        (
            {"data_inicio_de": date(2026, 10, 20), "data_inicio_ate": date(2026, 10, 10)},
            "data_inicio_de não pode ser posterior a data_inicio_ate",
        ),
    ],
)
def test_atividade_filter_valida_intervalos_de_datas_invalidos(dados_datas, mensagem_erro):
    with pytest.raises(ValidationError) as exc_info:
        AtividadeFilter(**dados_datas)

    assert mensagem_erro in str(exc_info.value)


@pytest.mark.parametrize(
    "dados_datas",
    [
        {"prazo_inicio": date(2026, 10, 1), "prazo_fim": date(2026, 10, 31)},
        {"prazo_inicio": date(2026, 10, 1), "prazo_fim": date(2026, 10, 1)},
        {"data_inicio_de": date(2026, 10, 10), "data_inicio_ate": date(2026, 10, 20)},
        {"data_inicio_de": date(2026, 10, 10), "data_inicio_ate": date(2026, 10, 10)},
    ],
)
def test_atividade_filter_valida_intervalos_de_datas_validos(dados_datas):
    filtro = AtividadeFilter(**dados_datas)
    for campo, valor in dados_datas.items():
        assert getattr(filtro, campo) == valor


@pytest.mark.parametrize(
    ("campo", "tamanho"),
    [
        ("titulo", 101),
        ("descricao", 256),
    ],
)
def test_atividade_filter_limite_maximo_dos_campos(campo, tamanho):
    dados = {campo: "a" * tamanho}
    with pytest.raises(ValidationError):
        AtividadeFilter(**dados)
