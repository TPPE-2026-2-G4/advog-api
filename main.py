import os

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)

import logging  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from typing import cast  # noqa: E402

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from starlette.types import ExceptionHandler  # noqa: E402

from app.atividade.controller import router as atividade_router  # noqa: E402
from app.atividade_funcionario.controller import (  # noqa: E402
    router as atividade_funcionario_router,
)
from app.atuacao.controller import router as atuacao_router  # noqa: E402
from app.auth.controller import router as auth_router  # noqa: E402
from app.cargo.controller import router as cargo_router  # noqa: E402
from app.categoria_lancamento.controller import router as categoria_lancamento_router  # noqa: E402
from app.cliente.controller import router as cliente_router  # noqa: E402
from app.cliente_arquivo.model import ClienteArquivo  # noqa: E402, F401
from app.config.database import Base, engine  # noqa: E402
from app.config.limiter import limiter  # noqa: E402
from app.dashboard.controller import router as dashboard_router  # noqa: E402
from app.funcionario.controller import router as funcionario_router  # noqa: E402
from app.institucional.controller import router as institucional_router  # noqa: E402
from app.lancamento.controller import router as lancamento_router  # noqa: E402
from app.processo.controller import router as processo_router  # noqa: E402
from app.processo.service import ProcessoService  # noqa: E402

Base.metadata.create_all(bind=engine)


logger = logging.getLogger("advog-api")


@asynccontextmanager
async def lifespan(app: FastAPI):

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        ProcessoService.sincronizar_processos_com_api, "interval", hours=12, id="sync_datajud"
    )
    scheduler.start()
    logger.info("Scheduler iniciado para jobs em background.")
    yield

    scheduler.shutdown()
    logger.info("Scheduler encerrado.")


app = FastAPI(
    title="Advocacia API",
    description="API para gestão de processos da advocacia",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(ExceptionHandler, _rate_limit_exceeded_handler))

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

app.include_router(auth_router)
app.include_router(atividade_router)
app.include_router(atividade_funcionario_router)
app.include_router(atuacao_router)
app.include_router(cargo_router)
app.include_router(funcionario_router)
app.include_router(institucional_router)
app.include_router(lancamento_router)
app.include_router(categoria_lancamento_router)
app.include_router(cliente_router)
app.include_router(processo_router)
app.include_router(dashboard_router)


@app.get("/")
def root():
    return {"message": "Bem vindo a API de Gestão de Advocacia (FastAPI)"}
