import os
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET") or "advog-jwt-secret-key-development-minimum-32-chars-long"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

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


def criar_token_acesso(dados: dict, tempo_expiracao_minutos: int = JWT_EXPIRATION_MINUTES) -> str:
    payload = dados.copy()
    agora = datetime.now(UTC)
    expiracao = agora + timedelta(minutes=tempo_expiracao_minutos)
    payload.update({"exp": expiracao, "iat": agora})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
