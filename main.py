import os

from dotenv import load_dotenv

load_dotenv()
load_dotenv(
    ".env.local", override=True
)  # overrides p/ rodar localmente fora do Docker (ver .env.local.example)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from app.config.database import Base, engine  # noqa: E402
from app.config.limiter import limiter  # noqa: E402
from app.controllers import auth, funcionario, processo_controller  # noqa: E402

# Cria as tabelas no banco de dados, caso não existam (SQLite development mode)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Advocacia API", description="API para gestão de processos da advocacia", version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

FRONTEND_URLS = [
    origem.strip()
    for origem in os.getenv("FRONTEND_URL", "http://localhost:3000").split(",")
    if origem.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(processo_controller.router)
app.include_router(funcionario.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {"message": "Bem vindo a API de Gestão de Advocacia (FastAPI)"}
