from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.limiter import limiter
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import AuthService, ContaNaoAtivaError, CredenciaisInvalidasError

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autenticar funcionário",
    responses={
        200: {
            "description": "Login realizado com sucesso. Retorna o token JWT e dados do usuário."
        },
        401: {"description": "Credenciais inválidas (e-mail ou senha incorretos)."},
        403: {"description": "Conta com status pendente de ativação ou inativa."},
        422: {"description": "Dados de requisição inválidos."},
        429: {
            "description": "Limite de tentativas excedido (Rate Limit: 10 requisições por minuto)."
        },
    },
)
@limiter.limit("10/minute")
def login(request: Request, dados: LoginRequest, db: Session = Depends(get_db)):
    # Realiza o login de funcionários com e-mail e senha. Retorna um token JWT válido por 60 minutos e os dados cadastrais do funcionário logado

    service = AuthService(db)
    try:
        token, funcionario = service.autenticar(dados)
        return TokenResponse(access_token=token, token_type="bearer", funcionario=funcionario)
    except CredenciaisInvalidasError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    except ContaNaoAtivaError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
