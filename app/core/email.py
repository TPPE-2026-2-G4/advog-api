import os
from html import escape
from typing import cast

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr, NameEmail, SecretStr

from app.core.seguranca import criar_token_primeiro_acesso

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("SMTP_USER", ""),
    MAIL_PASSWORD=SecretStr(os.getenv("SMTP_PASSWORD", "")),
    MAIL_FROM=cast(EmailStr, os.getenv("SMTP_FROM") or "nao-responda@escritorio.com.br"),
    MAIL_PORT=int(os.getenv("SMTP_PORT", "1025")),
    MAIL_SERVER=os.getenv("SMTP_HOST", "localhost"),
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=False,
)

BASE_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
LINK_PRIMEIRO_ACESSO = BASE_FRONTEND_URL + "/primeiro-acesso"
LINK_RECUPERACAO_SENHA = BASE_FRONTEND_URL + "/redefinir-senha"
FONT_FAMILY = "Georgia, 'Times New Roman', serif"


async def enviar_email_boas_vindas(email_destino: str, nome: str, funcionario_id: int):
    token = criar_token_primeiro_acesso(funcionario_id)
    link_primeiro_acesso = f"{LINK_PRIMEIRO_ACESSO}?token={token}"
    mensagem = MessageSchema(
        subject="Bem-vindo(a) ao escritório",
        recipients=[cast(NameEmail, email_destino)],
        body=f"""
        <div style="background-color:#f4f2ed; padding:32px 16px; font-family:{FONT_FAMILY};">
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
                  É com satisfação que confirmamos a criação da sua conta em nosso sistema!
                  Para dar continuidade, acesse a plataforma através do botão abaixo, onde você
                  poderá finalizar seu cadastro e definir sua senha de acesso.
                </p>
                <div style="text-align:center; margin:32px 0;">
                  <a href="{link_primeiro_acesso}" style="background-color:#0c2340; color:#c9a44c; text-decoration:none; padding:14px 32px; font-size:15px; letter-spacing:0.5px; display:inline-block;">
                    ACESSAR MINHA CONTA
                  </a>
                </div>
                <p style="font-size:13px; color:#666666; line-height:1.6;">
                  Caso o botão acima não funcione, copie e cole o endereço abaixo em seu navegador:<br>
                  <a href="{link_primeiro_acesso}" style="color:#0c2340;">{link_primeiro_acesso}</a>
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


async def enviar_email_recuperacao_senha(email_destino: str, nome: str, token: str):
    link = f"{LINK_RECUPERACAO_SENHA}?token={token}"
    mensagem = MessageSchema(
        subject="Redefinição de senha",
        recipients=[cast(NameEmail, email_destino)],
        body=f"""
        <div style="background-color:#f4f2ed; padding:32px 16px; font-family:{FONT_FAMILY};">
          <table role="presentation" width="100%" style="max-width:520px; margin:0 auto; background-color:#ffffff; border:1px solid #e2ddd1; font-family:{FONT_FAMILY};">
            <tr>
              <td style="background-color:#0c2340; padding:24px 32px; text-align:center; font-family:{FONT_FAMILY};">
                <span style="color:#c9a44c; font-size:22px; letter-spacing:1px; text-transform:uppercase; font-family:{FONT_FAMILY};">Escritório de Advocacia</span>
              </td>
            </tr>
            <tr>
              <td style="padding:32px; font-family:{FONT_FAMILY};">
                <h2 style="color:#0c2340; font-family:{FONT_FAMILY};">Redefinição de senha</h2>
                <p style="font-family:{FONT_FAMILY};">Olá, <strong>{escape(nome)}</strong>.</p>
                <p style="font-family:{FONT_FAMILY};">Recebemos uma solicitação para redefinir sua senha. O link abaixo é válido por 30 minutos e pode ser usado uma única vez.</p>
                <div style="text-align:center; margin:32px 0; font-family:{FONT_FAMILY};">
                  <a href="{link}" style="background-color:#0c2340; color:#c9a44c; text-decoration:none; padding:14px 24px; font-size:15px; letter-spacing:0.5px; display:inline-block; font-family:{FONT_FAMILY};">REDEFINIR MINHA SENHA</a>
                </div>
                <p style="font-size:13px; color:#6b7280; line-height:1.6; font-family:{FONT_FAMILY};">Se você não solicitou isso, ignore este e-mail.</p>
              </td>
            </tr>
          </table>
        </div>
        """,
        subtype=MessageType.html,
    )
    await FastMail(conf).send_message(mensagem)
