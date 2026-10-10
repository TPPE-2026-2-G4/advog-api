from sqlalchemy.orm import Session

from app.solicitacao.repository import SolicitacaoRepository
from app.solicitacao.schema import SolicitacaoCreate


def test_criar_solicitacao_sucesso(db: Session):
    repo = SolicitacaoRepository(db)
    payload = SolicitacaoCreate(
        nome="Carlos Oliveira",
        email="carlos.oliveira@email.com",
        telefone="61999998888",
        descricao="Solicitação de atendimento para análise jurídica.",
    )

    cliente = repo.criar_solicitacao_cliente(payload)

    assert cliente.id is not None
    assert cliente.nome == "Carlos Oliveira"
    assert cliente.email == "carlos.oliveira@email.com"
    assert cliente.telefone == "61999998888"
    assert cliente.descricao == "Solicitação de atendimento para análise jurídica."
    assert cliente.etapa_id == 1
    assert cliente.responsavel_id is None
    assert cliente.ultima_interacao is not None


def test_permitir_multiplas_solicitacoes_mesmo_email(db: Session):
    repo = SolicitacaoRepository(db)
    payload_1 = SolicitacaoCreate(
        nome="Mariana Costa",
        email="mariana@email.com",
        telefone="61988887777",
        descricao="Primeira solicitação de consultoria.",
    )
    payload_2 = SolicitacaoCreate(
        nome="Mariana Costa",
        email="mariana@email.com",
        telefone="61988887777",
        descricao="Segunda solicitação de consultoria para outro caso.",
    )

    cliente_1 = repo.criar_solicitacao_cliente(payload_1)
    cliente_2 = repo.criar_solicitacao_cliente(payload_2)

    assert cliente_1.id != cliente_2.id
    assert cliente_1.email == cliente_2.email
