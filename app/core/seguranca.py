import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.config.ambiente import obter_environment

DEV_SECRET_KEY = "advog-jwt-secret-key-development-minimum-32-chars-long"
DEV_SECRET_KEYS = {
    DEV_SECRET_KEY,
    "dev",
    "development",
    "secret",
    "changeme",
}


SECRET_KEY_TAMANHO_MINIMO = 32


def validar_secret_key(chave: str | None, environment: str) -> str:
    env = (environment or "").strip().lower()
    if env == "production":
        if not chave or not chave.strip():
            raise RuntimeError("SECRET_KEY é obrigatória em ambiente de produção.")
        if chave.strip() in DEV_SECRET_KEYS:
            raise RuntimeError(
                "SECRET_KEY não pode ser o valor padrão de desenvolvimento em ambiente de produção."
            )
        if len(chave.strip()) < SECRET_KEY_TAMANHO_MINIMO:
            raise RuntimeError(
                f"SECRET_KEY deve ter pelo menos {SECRET_KEY_TAMANHO_MINIMO} caracteres "
                "em ambiente de produção."
            )
        return chave.strip()

    if not chave or not chave.strip():
        return DEV_SECRET_KEY
    return chave.strip()


ENVIRONMENT = obter_environment()
SECRET_KEY = validar_secret_key(os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET"), ENVIRONMENT)
JWT_SECRET = SECRET_KEY
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

TOKEN_PRIMEIRO_ACESSO_TIPO = "primeiro_acesso"
TOKEN_PRIMEIRO_ACESSO_MINUTOS = 60 * 24

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    argon2__type="ID",
    argon2__memory_cost=19456,
    argon2__time_cost=2,
    argon2__parallelism=1,
)


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha, senha_hash)


def criar_token_recuperacao() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def hash_token_recuperacao(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def criar_token_acesso(dados: dict, tempo_expiracao_minutos: int = JWT_EXPIRATION_MINUTES) -> str:
    payload = dados.copy()
    agora = datetime.now(UTC)
    expiracao = agora + timedelta(minutes=tempo_expiracao_minutos)
    payload.update({"exp": expiracao, "iat": agora})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], leeway=5)


def criar_token_primeiro_acesso(funcionario_id: int) -> str:
    return criar_token_acesso(
        {"funcionario_id": funcionario_id, "tipo": TOKEN_PRIMEIRO_ACESSO_TIPO},
        tempo_expiracao_minutos=TOKEN_PRIMEIRO_ACESSO_MINUTOS,
    )


def validar_token_primeiro_acesso(token: str) -> int:
    try:
        payload = decodificar_token(token)
    except jwt.PyJWTError as e:
        raise ValueError("Token de primeiro acesso inválido ou expirado") from e

    if payload.get("tipo") != TOKEN_PRIMEIRO_ACESSO_TIPO:
        raise ValueError("Token de primeiro acesso inválido")

    return int(payload["funcionario_id"])


def extrair_funcionario_id_do_token(token: str) -> int:
    try:
        payload = decodificar_token(token)
    except jwt.PyJWTError as e:
        raise ValueError("Token inválido ou expirado") from e

    sub = payload.get("sub")
    if sub is None:
        raise ValueError("Token inválido")

    return int(sub)
