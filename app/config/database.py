import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config.ambiente import obter_environment


def validar_database_url(url: str | None, environment: str) -> str:
    env = (environment or "").strip().lower()
    if env == "production":
        if not url or not url.strip():
            raise RuntimeError("DATABASE_URL é obrigatória no ambiente de produção.")
        if url.strip().startswith("sqlite"):
            raise RuntimeError("Fallback para SQLite não é permitido no ambiente de produção.")
    elif not url or not url.strip():
        return "sqlite:///./advog_db.sqlite"

    url_limpa = (url or "").strip()
    if url_limpa.startswith("postgres://"):
        url_limpa = url_limpa.replace("postgres://", "postgresql://", 1)

    return url_limpa


ENVIRONMENT = obter_environment()
DATABASE_URL = validar_database_url(os.getenv("DATABASE_URL"), ENVIRONMENT)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine_kwargs: dict[str, Any] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
if not (DATABASE_URL.startswith("sqlite") and ":memory:" in DATABASE_URL):
    engine_kwargs["pool_timeout"] = 30

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
