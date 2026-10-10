from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.limiter import limiter
from app.solicitacao.schema import SolicitacaoCreate, SolicitacaoResponse
from app.solicitacao.service import SolicitacaoService

router = APIRouter(prefix="/solicitacoes", tags=["Solicitações"])


@router.post(
    "",
    response_model=SolicitacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def registrar_solicitacao(
    request: Request,
    solicitacao: SolicitacaoCreate,
    db: Session = Depends(get_db),
):
    service = SolicitacaoService(db)
    return service.registrar_solicitacao(solicitacao)
