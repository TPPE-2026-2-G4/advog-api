import os
from typing import cast

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr, NameEmail, SecretStr

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("SMTP_USER", ""),
    MAIL_PASSWORD=SecretStr(os.getenv("SMTP_PASSWORD", "")),
    MAIL_FROM=cast(EmailStr, os.getenv("SMTP_FROM", "")),
    MAIL_PORT=int(os.getenv("SMTP_PORT", "1025")),
    MAIL_SERVER=os.getenv("SMTP_HOST", ""),
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=False,
)

LINK_LOGIN = "https://www.google.com"  # TODO: substituir pelo link da página de login quando estiver disponível


async def enviar_email_boas_vindas(email_destino: str, nome: str):
    mensagem = MessageSchema(
        subject="Bem-vindo(a) ao escritório",
        recipients=[cast(NameEmail, email_destino)],
        body=f"""
        <div style="background-color:#f4f2ed; padding:32px 16px; font-family:Georgia,'Times New Roman',serif;">
          <table role="presentation" width="100%" style="max-width:520px; margin:0 auto; background-color:#ffffff; border:1px solid #e2ddd1;">
            <tr>
              <td style="background-color:#0c2340; padding:24px 32px; text-align:center;">
                <span style="color:#c9a44c; font-size:22px; letter-spacing:1px; text-transform:uppercase;">Escritório de Advocacia</span>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <p style="font-size:16px; color:#1a1a1a; margin-top:0;">Prezado(a) <strong>{nome}</strong>,</p>
                <p style="font-size:15px; color:#333333; line-height:1.6;">
                  É com satisfação que confirmamos a criação da sua conta em nosso sistema.
                  Para dar continuidade, acesse a plataforma através do botão abaixo, onde você
                  poderá finalizar seu cadastro e definir sua senha de acesso.
                </p>
                <div style="text-align:center; margin:32px 0;">
                  <a href="{LINK_LOGIN}" style="background-color:#0c2340; color:#c9a44c; text-decoration:none; padding:14px 32px; font-size:15px; letter-spacing:0.5px; display:inline-block;">
                    ACESSAR MINHA CONTA
                  </a>
                </div>
                <p style="font-size:13px; color:#666666; line-height:1.6;">
                  Caso o botão acima não funcione, copie e cole o endereço abaixo em seu navegador:<br>
                  <a href="{LINK_LOGIN}" style="color:#0c2340;">{LINK_LOGIN}</a>
                </p>
                <p style="font-size:14px; color:#333333; margin-bottom:0;">Atenciosamente,<br>Equipe do Escritório</p>
              </td>
            </tr>
          </table>
        </div>
        """,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(mensagem)
