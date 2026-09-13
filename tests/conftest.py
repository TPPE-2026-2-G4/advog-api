from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import database
from app.config.database import Base, get_db
from app.models.cargo import Cargo

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)

database.engine = engine
database.SessionLocal = TestingSessionLocal

from main import app  # noqa: E402


@pytest.fixture(autouse=True)
def mock_enviar_email_boas_vindas(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("app.controllers.funcionario.enviar_email_boas_vindas", mock)
    return mock


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def cargo_padrao(db_session: Session) -> Cargo:
    cargo = Cargo()
    cargo.nome_cargo = "Advogado Padrão"
    cargo.descricao = "Cargo de testes"
    cargo.permissao = {}
    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)
    return cargo
