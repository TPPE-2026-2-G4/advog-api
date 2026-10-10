from sqlalchemy.orm import Session

from app.solicitacao.repository import SolicitacaoRepository
from app.solicitacao.schema import SolicitacaoCreate


def test_criar_solicitacao_sucesso(db_session: Session):
    repository = SolicitacaoRepository(db_session)
    dados_solicitacao = SolicitacaoCreate(
        nome="Carlos Oliveira",
        email="carlos.oliveira@email.com",
        telefone="61999998888",
        descricao="Solicitação de atendimento para análise jurídica.",
    )

    cliente_criado = repository.criar_solicitacao_cliente(dados_solicitacao)

    assert cliente_criado.cliente_id is not None
    assert cliente_criado.nome == "Carlos Oliveira"
    assert cliente_criado.email == "carlos.oliveira@email.com"
    assert cliente_criado.telefone == "61999998888"
    assert cliente_criado.descricao == "Solicitação de atendimento para análise jurídica."
    assert cliente_criado.etapa_id == 1
    assert cliente_criado.responsavel_id is None
    assert cliente_criado.ultima_interacao is not None


def test_permitir_multiplas_solicitacoes_mesmo_email(db_session: Session):
    repository = SolicitacaoRepository(db_session)
    dados_primeira_solicitacao = SolicitacaoCreate(
        nome="Mariana Costa",
        email="mariana@email.com",
        telefone="61888887777",
        descricao="Primeira solicitação de consultoria.",
    )
    dados_segunda_solicitacao = SolicitacaoCreate(
        nome="Mariana Costa",
        email="mariana@email.com",
        telefone="61888887777",
        descricao="Segunda solicitação de consultoria para outro caso.",
    )

    primeira_solicitacao = repository.criar_solicitacao_cliente(dados_primeira_solicitacao)
    segunda_solicitacao = repository.criar_solicitacao_cliente(dados_segunda_solicitacao)

    assert primeira_solicitacao.cliente_id != segunda_solicitacao.cliente_id
    assert primeira_solicitacao.email == segunda_solicitacao.email
