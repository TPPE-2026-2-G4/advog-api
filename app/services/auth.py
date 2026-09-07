from sqlalchemy.orm import Session

from app.models.funcionario import Funcionario, StatusFuncionario
from app.repositories.funcionario import FuncionarioRepository
from app.schemas.auth import LoginRequest
from app.utils.seguranca import criar_token_acesso, verificar_senha


class CredenciaisInvalidasError(ValueError):
    pass


class ContaNaoAtivaError(ValueError):
    pass


class AuthService:
    def __init__(self, db_session: Session):
        self.repository = FuncionarioRepository(db_session)

    def autenticar(self, dados: LoginRequest) -> tuple[str, Funcionario]:
        funcionario = self.repository.buscar_por_email(dados.email.strip().lower())
        if not funcionario or not funcionario.senha_hash:
            raise CredenciaisInvalidasError("Email ou senha incorretos")

        if not verificar_senha(dados.senha, funcionario.senha_hash):
            raise CredenciaisInvalidasError("Email ou senha incorretos")

        if funcionario.status == StatusFuncionario.PENDENTE:
            raise ContaNaoAtivaError("Conta pendente de ativação. Realize o primeiro acesso.")

        if funcionario.status == StatusFuncionario.INATIVO:
            raise ContaNaoAtivaError("Conta inativa. Entre em contato com o administrador.")

        token = criar_token_acesso(
            {
                "sub": str(funcionario.funcionario_id),
                "email": funcionario.email,
            }
        )
        return token, funcionario
