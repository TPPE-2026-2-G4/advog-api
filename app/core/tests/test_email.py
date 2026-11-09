import re
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.email import enviar_email_boas_vindas, enviar_email_recuperacao_senha
from app.core.seguranca import validar_token_primeiro_acesso


@pytest.fixture(autouse=True)
def sem_brevo_por_padrao(monkeypatch):
    monkeypatch.setattr("app.core.email.BREVO_API_KEY", "")


def _resposta_brevo(status_code: int) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={"messageId": "<id>"},
        request=httpx.Request("POST", "https://api.brevo.com/v3/smtp/email"),
    )


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


@pytest.mark.asyncio
async def test_com_brevo_envia_pela_api_https_e_nao_por_smtp(monkeypatch):
    monkeypatch.setattr("app.core.email.BREVO_API_KEY", "chave-brevo-teste")
    monkeypatch.setattr("app.core.email.EMAIL_REMETENTE", "remetente@escritorio.com")
    monkeypatch.setattr("app.core.email.EMAIL_NOME_REMETENTE", "Escritório Teste")

    with (
        patch("app.core.email.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch("app.core.email.FastMail.send_message", new_callable=AsyncMock) as mock_smtp,
    ):
        mock_post.return_value = _resposta_brevo(201)
        await enviar_email_recuperacao_senha("pytest@teste.com", "PyTest User", "token-teste")

    mock_smtp.assert_not_called()
    mock_post.assert_awaited_once()
    assert mock_post.call_args.args[0] == "https://api.brevo.com/v3/smtp/email"
    assert mock_post.call_args.kwargs["headers"]["api-key"] == "chave-brevo-teste"
    corpo = mock_post.call_args.kwargs["json"]
    assert corpo["sender"] == {"name": "Escritório Teste", "email": "remetente@escritorio.com"}
    assert corpo["to"] == [{"email": "pytest@teste.com"}]
    assert corpo["subject"] == "Redefinição de senha"
    assert "token=token-teste" in corpo["htmlContent"]


@pytest.mark.asyncio
async def test_com_brevo_propaga_erro_da_api(monkeypatch):
    monkeypatch.setattr("app.core.email.BREVO_API_KEY", "chave-brevo-teste")

    with patch("app.core.email.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _resposta_brevo(401)
        with pytest.raises(httpx.HTTPStatusError):
            await enviar_email_boas_vindas("pytest@teste.com", "PyTest User", 42)
