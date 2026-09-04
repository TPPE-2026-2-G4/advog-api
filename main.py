from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local", override=True)  # overrides p/ rodar localmente fora do Docker (ver .env.local.example)

from fastapi import FastAPI
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

app.include_router(processo_controller.router)
app.include_router(funcionario.router)

@app.get("/")
def root():
    return {"message": "Bem vindo a API de Gestão de Advocacia (FastAPI)"}
