from unittest.mock import MagicMock

from app.solicitacao.schema import SolicitacaoCreate
from app.solicitacao.service import SolicitacaoService


def test_registrar_solicitacao_service_sucesso():
    db_mock = MagicMock()
    service = SolicitacaoService(db_mock)
    service.solicitacao_repo = MagicMock()

    payload = SolicitacaoCreate(
        nome="Lucas Mendes",
        email="lucas@email.com",
        telefone="61999998888",
        descricao="Solicito assessoria para elaboração de contrato de prestação de serviços.",
    )

    cliente_ficticio = MagicMock()
    cliente_ficticio.id = 42
    cliente_ficticio.nome = "Lucas Mendes"
    service.solicitacao_repo.criar_solicitacao_cliente.return_value = cliente_ficticio

    resultado = service.registrar_solicitacao(payload)

    service.solicitacao_repo.criar_solicitacao_cliente.assert_called_once_with(payload)
    assert resultado.id == 42
    assert resultado.nome == "Lucas Mendes"
