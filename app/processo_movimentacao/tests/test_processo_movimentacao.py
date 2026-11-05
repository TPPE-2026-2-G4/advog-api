from app.processo_movimentacao.model import ProcessoMovimentacao, TipoMovimentacaoProcesso


def test_criar_e_listar_movimentacoes_do_processo(db_session):
    mov1 = ProcessoMovimentacao(
        processo_id=1,
        funcionario_id=2,
        tipo_movimentacao=TipoMovimentacaoProcesso.CRIACAO_PROCESSO,
        descricao="Processo criado no sistema.",
    )
    mov2 = ProcessoMovimentacao(
        processo_id=1,
        funcionario_id=None,
        tipo_movimentacao=TipoMovimentacaoProcesso.UPLOAD_ARQUIVO,
        descricao="Arquivo 'peticao.pdf' adicionado ao processo.",
    )

    db_session.add_all([mov1, mov2])
    db_session.commit()

    registros = (
        db_session.query(ProcessoMovimentacao)
        .filter_by(processo_id=1)
        .order_by(ProcessoMovimentacao.movimentacao_id.asc())
        .all()
    )
    assert len(registros) == 2
    assert registros[0].movimentacao_id is not None
    assert registros[0].tipo_movimentacao == TipoMovimentacaoProcesso.CRIACAO_PROCESSO
    assert registros[0].funcionario_id == 2
    assert registros[0].data_movimentacao is not None
    assert registros[1].tipo_movimentacao == TipoMovimentacaoProcesso.UPLOAD_ARQUIVO
    assert registros[1].funcionario_id is None
