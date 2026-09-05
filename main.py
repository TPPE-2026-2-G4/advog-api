import os

from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local", override=True)  # overrides p/ rodar localmente fora do Docker (ver .env.local.example)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import engine, Base
from app.controllers import processo_controller
from app.controllers import funcionario

# Cria as tabelas no banco de dados, caso não existam (SQLite development mode)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Advocacia API",
    description="API para gestão de processos da advocacia",
    version="1.0.0"
)

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

@app.get("/")
def root():
    return {"message": "Bem vindo a API de Gestão de Advocacia (FastAPI)"}
