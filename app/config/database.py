import os
from typing import Any

from sqlalchemy import Engine, create_engine, inspect, text
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

CONEXAO_TIMEOUT_SEGUNDOS = 10

connect_args: dict[str, Any] = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {"connect_timeout": CONEXAO_TIMEOUT_SEGUNDOS}
)

engine_kwargs: dict[str, Any] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
if not (DATABASE_URL.startswith("sqlite") and ":memory:" in DATABASE_URL):
    engine_kwargs["pool_timeout"] = 30

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def garantir_colunas_schema(bind_engine: Engine = engine) -> None:
    try:
        inspector = inspect(bind_engine)
        if inspector.has_table("funcionarios"):
            colunas = {col["name"] for col in inspector.get_columns("funcionarios")}
            if "receber_emails" not in colunas:
                with bind_engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE funcionarios "
                            "ADD COLUMN receber_emails BOOLEAN NOT NULL DEFAULT TRUE"
                        )
                    )
    except Exception:
        pass

    _tornar_colunas_processo_opcionais(bind_engine)


COLUNAS_OPCIONAIS_PROCESSOS = ("descricao", "funcionario_id")


def _tornar_colunas_processo_opcionais(bind_engine: Engine) -> None:
    """Remove o NOT NULL de colunas que passaram a ser opcionais em bancos já existentes.

    O SQLite não suporta ALTER COLUMN; nele a restrição só some ao recriar o banco.
    """
    if bind_engine.dialect.name != "postgresql":
        return

    try:
        inspector = inspect(bind_engine)
        if not inspector.has_table("processos"):
            return
        colunas = {col["name"]: col for col in inspector.get_columns("processos")}
        for nome in COLUNAS_OPCIONAIS_PROCESSOS:
            if nome in colunas and not colunas[nome]["nullable"]:
                with bind_engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE processos ALTER COLUMN {nome} DROP NOT NULL"))
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
