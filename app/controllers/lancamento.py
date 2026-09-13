from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.repositories.lancamento import LancamentoRepository
from app.schemas.lancamento import LancamentoCreate, LancamentoResponse
from app.services.lancamento import LancamentoService

router = APIRouter(prefix="/lancamentos", tags=["Finanças"])


def get_lancamento_service(db: Session = Depends(get_db)) -> LancamentoService:
    repository = LancamentoRepository(db)
    return LancamentoService(repository)


@router.get("/", response_model=list[LancamentoResponse])
def listar_lancamentos(service: LancamentoService = Depends(get_lancamento_service)):
    return service.list_lancamentos()


@router.post("/", response_model=LancamentoResponse, status_code=201)
def criar_lancamento(
    lancamento: LancamentoCreate, service: LancamentoService = Depends(get_lancamento_service)
):
    return service.create_lancamento(lancamento)
