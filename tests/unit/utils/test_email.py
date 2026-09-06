from unittest.mock import AsyncMock, patch

import pytest

from app.utils.email import enviar_email_boas_vindas


@pytest.mark.asyncio
async def test_enviar_boas_vindas_chama_send_message():
    with patch("app.utils.email.FastMail.send_message", new_callable=AsyncMock) as mock_send:
        await enviar_email_boas_vindas("pytest@teste.com", "PyTest User")

        mock_send.assert_called_once()
        mensagem_enviada = mock_send.call_args[0][0]

        email_destino = [destinatario.email for destinatario in mensagem_enviada.recipients]
        assert "pytest@teste.com" in email_destino
        assert "PyTest User" in mensagem_enviada.body
