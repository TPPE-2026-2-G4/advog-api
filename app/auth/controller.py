from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.schema import (
    LoginRequest,
    MensagemResponse,
    RedefinirSenha,
    SolicitarRecuperacaoSenha,
    TokenResponse,
)
from app.auth.service import (
    AuthService,
    ContaNaoAtivaError,
    CredenciaisInvalidasError,
    TokenRecuperacaoInvalidoError,
)
from app.config.database import get_db
from app.config.limiter import limiter
from app.core.email import enviar_email_recuperacao_senha
from app.funcionario.schema import FuncionarioResponse

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
    service = AuthService(db)
    try:
        token, funcionario = service.autenticar(dados)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            funcionario=FuncionarioResponse.model_validate(funcionario),
        )
    except CredenciaisInvalidasError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    except ContaNaoAtivaError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.post("/esqueci-senha", response_model=MensagemResponse)
@limiter.limit("5/minute")
def solicitar_recuperacao_senha(
    request: Request,
    dados: SolicitarRecuperacaoSenha,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    resultado = AuthService(db).solicitar_recuperacao(str(dados.email))
    if resultado:
        token, email, nome = resultado
        background_tasks.add_task(enviar_email_recuperacao_senha, email, nome, token)

    return MensagemResponse(
        mensagem="Se o e-mail estiver cadastrado, você receberá um link para redefinir sua senha."
    )


@router.post("/redefinir-senha", response_model=MensagemResponse)
def redefinir_senha(dados: RedefinirSenha, db: Session = Depends(get_db)):
    try:
        AuthService(db).redefinir_senha(dados)
    except TokenRecuperacaoInvalidoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return MensagemResponse(mensagem="Senha redefinida com sucesso.")
