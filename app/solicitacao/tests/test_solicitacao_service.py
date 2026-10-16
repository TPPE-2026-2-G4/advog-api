from unittest.mock import MagicMock

from app.solicitacao.schema import SolicitacaoCreate
from app.solicitacao.service import SolicitacaoService


def test_registrar_solicitacao_service_sucesso():
    sessao_banco_mock = MagicMock()
    servico = SolicitacaoService(sessao_banco_mock)
    servico.solicitacao_repo = MagicMock()

    dados_solicitacao = SolicitacaoCreate(
        nome="Lucas Mendes",
        email="lucas@email.com",
        telefone="61999998888",
        descricao="Solicito assessoria para elaboração de contrato de prestação de serviços.",
    )

    cliente_ficticio = MagicMock()
    cliente_ficticio.cliente_id = 42
    cliente_ficticio.nome = "Lucas Mendes"
    servico.solicitacao_repo.criar_solicitacao_cliente.return_value = cliente_ficticio

    resultado = servico.registrar_solicitacao(dados_solicitacao)

    servico.solicitacao_repo.criar_solicitacao_cliente.assert_called_once_with(dados_solicitacao)
    assert resultado.cliente_id == 42
    assert resultado.nome == "Lucas Mendes"
