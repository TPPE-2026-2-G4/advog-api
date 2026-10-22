import pytest
from pydantic import ValidationError

from app.processo.model import StatusProcesso
from app.processo.schema import (
    ProcessoCreate,
    ProcessoFilter,
    ProcessoResponse,
    ProcessoUpdate,
)


def processo_valido() -> dict:
    return {
        "cnj": "11111111111111111111",
        "titulo": "Processo Teste",
        "descricao": "Descrição do processo",
        "status": StatusProcesso.ATIVO,
        "tribunal": "TJSP",
        "area": "Civil",
        "data_inicio": "2026-01-01T00:00:00",
        "data_realizado": "2026-01-10T00:00:00",
        "data_prazo": "2026-12-31T00:00:00",
        "cliente_id": 1,
        "funcionario_id": 1,
    }


def test_processo_create_valido():
    processo = ProcessoCreate(**processo_valido())

    assert processo.cnj == "11111111111111111111"
    assert processo.titulo == "Processo Teste"
    assert processo.status == StatusProcesso.ATIVO
    assert processo.cliente_id == 1
    assert processo.funcionario_id == 1


def test_status_padrao_e_em_analise():
    dados = processo_valido()
    dados.pop("status")

    processo = ProcessoCreate(**dados)

    assert processo.status == StatusProcesso.EM_ANALISE


@pytest.mark.parametrize(
    "status",
    [
        StatusProcesso.EM_ANALISE,
        StatusProcesso.ATIVO,
        StatusProcesso.CONCLUIDO,
        StatusProcesso.ARQUIVADO,
    ],
)
def test_status_validos(status):
    dados = processo_valido()
    dados["status"] = status

    processo = ProcessoCreate(**dados)

    assert processo.status == status


def test_status_invalido():
    dados = processo_valido()
    dados["status"] = "Pendente"

    with pytest.raises(ValidationError):
        ProcessoCreate(**dados)


@pytest.mark.parametrize(
    ("campo", "tamanho"),
    [
        ("cnj", 26),
        ("titulo", 101),
        ("descricao", 256),
        ("tribunal", 101),
        ("area", 101),
    ],
)
def test_limite_maximo_dos_campos(campo, tamanho):
    dados = processo_valido()
    dados[campo] = "a" * tamanho

    with pytest.raises(ValidationError):
        ProcessoCreate(**dados)


@pytest.mark.parametrize(
    "campo",
    [
        "descricao",
        "data_inicio",
        "data_realizado",
        "data_prazo",
        "funcionario_id",
    ],
)
def test_campos_opcionais_podem_ser_nulos(campo):
    dados = processo_valido()
    dados[campo] = None

    processo = ProcessoCreate(**dados)

    assert getattr(processo, campo) is None


def test_cliente_id_e_obrigatorio():
    dados = processo_valido()
    dados.pop("cliente_id")

    with pytest.raises(ValidationError):
        ProcessoCreate(**dados)


def test_processo_update_aceita_atualizacao_parcial():
    processo = ProcessoUpdate(
        status=StatusProcesso.CONCLUIDO,
    )

    assert processo.status == StatusProcesso.CONCLUIDO
    assert processo.titulo is None
    assert processo.area is None


def test_processo_update_aceita_funcionario():
    processo = ProcessoUpdate(
        funcionario_id=10,
    )

    assert processo.funcionario_id == 10


def test_processo_filter():
    filtros = ProcessoFilter(
        processo_id=10,
        cnj="123",
        titulo="Teste",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=20,
        funcionario_id=30,
    )

    assert filtros.processo_id == 10
    assert filtros.cnj == "123"
    assert filtros.titulo == "Teste"
    assert filtros.descricao == "Descrição"
    assert filtros.status == StatusProcesso.ATIVO
    assert filtros.tribunal == "TJSP"
    assert filtros.area == "Civil"
    assert filtros.cliente_id == 20
    assert filtros.funcionario_id == 30


def test_processo_response():
    dados = processo_valido()
    dados["processo_id"] = 1

    response = ProcessoResponse(**dados)

    assert response.processo_id == 1
    assert response.funcionario_id == 1
