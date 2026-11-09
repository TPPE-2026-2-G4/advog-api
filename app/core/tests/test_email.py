import re
from unittest.mock import AsyncMock, patch

import pytest

from app.core.email import enviar_email_boas_vindas, enviar_email_recuperacao_senha
from app.core.seguranca import validar_token_primeiro_acesso


@pytest.mark.asyncio
async def test_enviar_boas_vindas_chama_send_message():
    with patch("app.core.email.FastMail.send_message", new_callable=AsyncMock) as mock_send:
        await enviar_email_boas_vindas("pytest@teste.com", "PyTest User", 42)

        mock_send.assert_called_once()
        mensagem_enviada = mock_send.call_args[0][0]

        email_destino = [destinatario.email for destinatario in mensagem_enviada.recipients]
        assert "pytest@teste.com" in email_destino
        assert "PyTest User" in mensagem_enviada.body

        token = re.search(r"token=([\w.\-]+)", mensagem_enviada.body).group(1)
        assert validar_token_primeiro_acesso(token) == 42


@pytest.mark.asyncio
async def test_enviar_recuperacao_senha_monta_email_com_link_e_fonte():
    with patch("app.core.email.FastMail.send_message", new_callable=AsyncMock) as mock_send:
        await enviar_email_recuperacao_senha("pytest@teste.com", "PyTest User", "token-teste")

        mock_send.assert_called_once()
        mensagem_enviada = mock_send.call_args[0][0]

        assert mensagem_enviada.subject == "Redefinição de senha"
        assert "PyTest User" in mensagem_enviada.body
        assert "token=token-teste" in mensagem_enviada.body
        assert "font-family:Georgia, 'Times New Roman', serif" in mensagem_enviada.body
