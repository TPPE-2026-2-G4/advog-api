from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.cargo.model import Cargo
from app.dashboard.service import DashboardService
from app.funcionario.model import Funcionario


@pytest.mark.parametrize(
    ("instante_utc", "inicio_esperado"),
    [
        (datetime(2026, 10, 15, 2, 59, 59, tzinfo=UTC), datetime(2026, 10, 14)),
        (datetime(2026, 10, 15, 3, tzinfo=UTC), datetime(2026, 10, 15)),
    ],
)
def test_resumo_usa_a_virada_do_dia_em_sao_paulo(instante_utc, inicio_esperado):
    service = DashboardService(MagicMock())
    service.repository = MagicMock()
    service.repository.resumir_atividades.return_value = {
        "pendentes": 0,
        "em_execucao": 0,
        "concluidas": 0,
        "atrasadas": 0,
    }
    funcionario = Funcionario(funcionario_id=1, cargo=Cargo(permissao={}))

    with patch("app.dashboard.service.datetime") as relogio:
        relogio.now.side_effect = instante_utc.astimezone
        relogio.combine.side_effect = datetime.combine
        resultado = service.resumir_atividades(funcionario)

    relogio.now.assert_called_once_with(ZoneInfo("America/Sao_Paulo"))
    service.repository.resumir_atividades.assert_called_once_with(inicio_esperado, funcionario_id=1)
    assert resultado.escopo == "usuario"
