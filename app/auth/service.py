from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.model import TokenRecuperacaoSenha
from app.auth.repository import TokenRecuperacaoSenhaRepository
from app.auth.schema import LoginRequest, RedefinirSenha
from app.core.seguranca import (
    criar_token_acesso,
    criar_token_recuperacao,
    hash_senha,
    hash_token_recuperacao,
    verificar_senha,
)
from app.funcionario.model import Funcionario, StatusFuncionario
from app.funcionario.repository import FuncionarioRepository


class CredenciaisInvalidasError(ValueError):
    pass


class ContaNaoAtivaError(ValueError):
    pass


class AuthService:
    def __init__(self, db_session: Session):
        self.repository = FuncionarioRepository(db_session)
        self.db = db_session
        self.tokens_repository = TokenRecuperacaoSenhaRepository(db_session)

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

    def solicitar_recuperacao(self, email: str) -> tuple[str, str, str] | None:
        funcionario = self.repository.buscar_por_email(email.strip().lower())
        if not funcionario or funcionario.status != StatusFuncionario.ATIVO:
            return None

        agora = datetime.now(UTC)
        token, token_hash = criar_token_recuperacao()
        self.tokens_repository.invalidar_tokens_ativos(funcionario.funcionario_id, agora)
        self.tokens_repository.criar(
            TokenRecuperacaoSenha(
                funcionario_id=funcionario.funcionario_id,
                token_hash=token_hash,
                criado_em=agora,
                expira_em=agora + timedelta(minutes=30),
            )
        )
        return token, funcionario.email, funcionario.nome

    def redefinir_senha(self, dados: RedefinirSenha) -> None:
        agora = datetime.now(UTC)
        token = self.tokens_repository.buscar_valido(hash_token_recuperacao(dados.token), agora)
        if not token:
            raise TokenRecuperacaoInvalidoError("Token inválido ou expirado")

        funcionario = self.repository.buscar_por_id(token.funcionario_id)
        if not funcionario or funcionario.status != StatusFuncionario.ATIVO:
            raise TokenRecuperacaoInvalidoError("Token inválido ou expirado")

        funcionario.senha_hash = hash_senha(dados.senha)
        token.usado_em = agora
        self.tokens_repository.invalidar_tokens_do_funcionario(funcionario.funcionario_id, agora)
        self.db.commit()


class TokenRecuperacaoInvalidoError(ValueError):
    pass
