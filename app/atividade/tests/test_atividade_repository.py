from datetime import datetime

import pytest
from sqlalchemy import event, insert

from app.atividade.model import Atividade
from app.atividade.repository import AtividadeRepository
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
