from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import event, insert

from app.atividade.model import Atividade
from app.atividade.repository import AtividadeRepository
from app.atividade.schema import AtividadeFilter
from app.atividade.service import AtividadeService
from app.atividade_funcionario.model import AtividadeFuncionario
from app.cargo.model import Cargo
from app.funcionario.model import Funcionario


def test_buscar_etapas_preserva_vazias_e_desempata_por_id(db_session, etapas):
    resultado = AtividadeRepository(db_session).buscar_etapas()

    assert [etapa.nome for etapa in resultado] == [
        "Backlog",
        "Em Execução",
        "Aguardando cliente",
        "Revisão",
        "Finalizado",
    ]
    assert len(resultado) == len(etapas)


@pytest.mark.parametrize(
    ("indice_usuario", "titulos"),
    [
        (None, ["propria", "terceiros", "compartilhada", "sem_responsavel", "finalizada"]),
        (0, ["propria", "compartilhada", "finalizada"]),
        (1, ["terceiros", "compartilhada"]),
    ],
)
def test_buscar_atividades_respeita_vinculos_sem_duplicar(
    db_session, atividades, funcionarios, indice_usuario, titulos
):
    funcionario_id = None if indice_usuario is None else funcionarios[indice_usuario].funcionario_id

    resultado = AtividadeRepository(db_session).buscar_atividades(funcionario_id)

    assert [atividade.titulo for atividade in resultado] == titulos
    assert [atividade.atividade_id for atividade in resultado] == sorted(
        atividades[titulo].atividade_id for titulo in titulos
    )


@pytest.mark.parametrize("titulo", [None, "compartilhada", "sem_responsavel"])
def test_buscar_responsaveis_somente_dos_cartoes_solicitados(
    db_session, atividades, funcionarios, titulo
):
    ids = [] if titulo is None else [atividades[titulo].atividade_id]

    resultado = AtividadeRepository(db_session).buscar_responsaveis(ids)

    esperado = []
    if titulo == "compartilhada":
        esperado = [
            (atividades[titulo].atividade_id, usuario.funcionario_id, usuario.nome)
            for usuario in funcionarios
        ]
    assert resultado == esperado


@pytest.mark.parametrize(
    ("filtros_params", "titulos_esperados"),
    [
        ({}, ["Elaborar Petição Inicial", "Revisão de Contrato", "Audiência de Conciliação"]),
        ({"busca_textual": "Petição"}, ["Elaborar Petição Inicial"]),
        ({"busca_textual": "Análise"}, ["Revisão de Contrato"]),
        ({"busca_textual": "Termo Inexistente"}, []),
        ({"etapa_nome": "Backlog"}, ["Elaborar Petição Inicial"]),
        ({"indice_funcionario": 1}, ["Revisão de Contrato", "Audiência de Conciliação"]),
        ({"com_processo": True}, ["Elaborar Petição Inicial", "Audiência de Conciliação"]),
        (
            {"prazo_inicio": date(2026, 10, 1), "prazo_fim": date(2026, 10, 31)},
            ["Elaborar Petição Inicial", "Revisão de Contrato"],
        ),
        (
            {"data_inicio_de": date(2026, 9, 1), "data_inicio_ate": date(2026, 9, 30)},
            ["Audiência de Conciliação"],
        ),
        ({"filtrar_por_id_de": "Elaborar Petição Inicial"}, ["Elaborar Petição Inicial"]),
        ({"titulo": "Petição"}, ["Elaborar Petição Inicial"]),
        ({"descricao": "Análise"}, ["Revisão de Contrato"]),
        ({"realizada": True}, []),
        (
            {"realizada": False},
            ["Elaborar Petição Inicial", "Revisão de Contrato", "Audiência de Conciliação"],
        ),
        ({"atrasada": True}, None),
        ({"atrasada": False}, None),
    ],
)
def test_buscar_por_filtros(
    db_session,
    atividades_para_filtro,
    etapas,
    funcionarios,
    processo,
    filtros_params,
    titulos_esperados,
):
    filtros_kwargs = {}

    if "filtrar_por_id_de" in filtros_params:
        atividade = (
            db_session.query(Atividade)
            .filter(Atividade.titulo == filtros_params["filtrar_por_id_de"])
            .first()
        )
        if atividade:
            filtros_kwargs["atividade_id"] = atividade.atividade_id
    if "titulo" in filtros_params:
        filtros_kwargs["titulo"] = filtros_params["titulo"]
    if "descricao" in filtros_params:
        filtros_kwargs["descricao"] = filtros_params["descricao"]
    if "busca_textual" in filtros_params:
        filtros_kwargs["busca_textual"] = filtros_params["busca_textual"]
    if "etapa_nome" in filtros_params:
        filtros_kwargs["etapa_id"] = etapas[filtros_params["etapa_nome"]].etapa_id
    if "indice_funcionario" in filtros_params:
        filtros_kwargs["funcionario_id"] = funcionarios[
            filtros_params["indice_funcionario"]
        ].funcionario_id
    if "com_processo" in filtros_params:
        filtros_kwargs["processo_id"] = (
            processo.processo_id if filtros_params["com_processo"] else None
        )
    if "prazo_inicio" in filtros_params:
        filtros_kwargs["prazo_inicio"] = filtros_params["prazo_inicio"]
    if "prazo_fim" in filtros_params:
        filtros_kwargs["prazo_fim"] = filtros_params["prazo_fim"]
    if "data_inicio_de" in filtros_params:
        filtros_kwargs["data_inicio_de"] = filtros_params["data_inicio_de"]
    if "data_inicio_ate" in filtros_params:
        filtros_kwargs["data_inicio_ate"] = filtros_params["data_inicio_ate"]
    if "realizada" in filtros_params:
        filtros_kwargs["realizada"] = filtros_params["realizada"]
    if "atrasada" in filtros_params:
        filtros_kwargs["atrasada"] = filtros_params["atrasada"]

    _ = AtividadeFilter.model_validate(filtros_kwargs)

    resultado = AtividadeRepository(db_session).buscar_por_filtros(**filtros_kwargs)

    titulos_obtidos = [atividade.titulo for atividade in resultado]
    if titulos_esperados is not None:
        assert sorted(titulos_obtidos) == sorted(titulos_esperados)
    else:
        assert isinstance(titulos_obtidos, list)


@pytest.mark.parametrize("quantidade", [0, 1, 5])
def test_kanban_executa_tres_consultas_sem_escrita(db_session, etapas, funcionarios, quantidade):
    etapa_id = etapas["Backlog"].etapa_id
    funcionario_id = funcionarios[0].funcionario_id
    if quantidade:
        db_session.execute(
            insert(Atividade),
            [
                {
                    "atividade_id": indice,
                    "titulo": f"Atividade {indice}",
                    "descricao": "Descrição",
                    "data_inicio": datetime(2026, 10, 1),
                    "data_prazo": datetime(2026, 10, 30),
                    "etapa_id": etapa_id,
                }
                for indice in range(1, quantidade + 1)
            ],
        )
        db_session.execute(
            insert(AtividadeFuncionario),
            [
                {"atividade_id": indice, "funcionario_id": funcionario_id}
                for indice in range(1, quantidade + 1)
            ],
        )
    db_session.commit()
    usuario = Funcionario(funcionario_id=funcionario_id, cargo=Cargo(permissao={}))
    comandos = []

    def registrar_comando(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement)

    conexao = db_session.connection()
    event.listen(conexao, "before_cursor_execute", registrar_comando)
    try:
        resultado = AtividadeService(db_session).visualizar_kanban(usuario)
    finally:
        event.remove(conexao, "before_cursor_execute", registrar_comando)

    assert len(comandos) == 3
    assert all(comando.lstrip().upper().startswith("SELECT") for comando in comandos)
    assert sum(len(etapa.atividades) for etapa in resultado.etapas) == quantidade
    assert db_session.query(Atividade).count() == quantidade
    assert db_session.query(AtividadeFuncionario).count() == quantidade


def test_produtividade_categorias_exclusivas_e_responsaveis(db_session, etapas, funcionarios):
    hoje = datetime(2026, 10, 22)
    casos = [
        ("Backlog", hoje),
        ("Em Execução", hoje),
        ("Revisão", hoje + timedelta(days=1)),
        ("Aguardando cliente", hoje),
        ("Backlog", hoje - timedelta(seconds=1)),
        ("Em Execução", hoje - timedelta(days=1)),
        ("Revisão", hoje - timedelta(days=1)),
        ("Finalizado", hoje - timedelta(days=1)),
    ]
    for indice, (etapa, prazo) in enumerate(casos):
        atividade = Atividade(
            titulo=f"Atividade {indice}",
            descricao="Teste",
            data_inicio=hoje - timedelta(days=2),
            data_prazo=prazo,
            etapa_id=etapas[etapa].etapa_id,
        )
        db_session.add(atividade)
        db_session.flush()
        db_session.add(
            AtividadeFuncionario(
                atividade_id=atividade.atividade_id,
                funcionario_id=funcionarios[0].funcionario_id,
            )
        )
        if etapa == "Finalizado":
            db_session.add(
                AtividadeFuncionario(
                    atividade_id=atividade.atividade_id,
                    funcionario_id=funcionarios[1].funcionario_id,
                )
            )
    db_session.flush()
    resultado = AtividadeRepository(db_session).buscar_produtividade_equipe(hoje)
    assert resultado == [
        {
            "funcionario_id": funcionarios[0].funcionario_id,
            "nome": funcionarios[0].nome,
            "finalizadas": 1,
            "a_fazer": 1,
            "em_andamento": 3,
            "atrasadas": 3,
        },
        {
            "funcionario_id": funcionarios[1].funcionario_id,
            "nome": funcionarios[1].nome,
            "finalizadas": 1,
            "a_fazer": 0,
            "em_andamento": 0,
            "atrasadas": 0,
        },
    ]


def test_produtividade_funcionarios_sem_atividades(db_session, funcionarios):
    resultado = AtividadeRepository(db_session).buscar_produtividade_equipe(datetime(2026, 10, 22))
    assert len(resultado) == 2
    for linha in resultado:
        assert all(
            linha[campo] == 0 for campo in ("finalizadas", "a_fazer", "em_andamento", "atrasadas")
        )


def test_produtividade_equipe_vazia(db_session):
    assert AtividadeRepository(db_session).buscar_produtividade_equipe(datetime(2026, 10, 22)) == []
