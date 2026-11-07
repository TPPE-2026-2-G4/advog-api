from datetime import datetime

from sqlalchemy.orm import Session

from app.auth.model import TokenRecuperacaoSenha


class TokenRecuperacaoSenhaRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def invalidar_tokens_ativos(self, funcionario_id: int, agora: datetime) -> None:
        tokens = (
            self.db.query(TokenRecuperacaoSenha)
            .filter(
                TokenRecuperacaoSenha.funcionario_id == funcionario_id,
                TokenRecuperacaoSenha.usado_em.is_(None),
                TokenRecuperacaoSenha.expira_em > agora,
            )
            .all()
        )
        for token in tokens:
            token.usado_em = agora

    def criar(self, token: TokenRecuperacaoSenha) -> TokenRecuperacaoSenha:
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def buscar_valido(self, token_hash: str, agora: datetime) -> TokenRecuperacaoSenha | None:
        return (
            self.db.query(TokenRecuperacaoSenha)
            .filter(
                TokenRecuperacaoSenha.token_hash == token_hash,
                TokenRecuperacaoSenha.usado_em.is_(None),
                TokenRecuperacaoSenha.expira_em > agora,
            )
            .first()
        )

    def invalidar_tokens_do_funcionario(self, funcionario_id: int, agora: datetime) -> None:
        tokens = (
            self.db.query(TokenRecuperacaoSenha)
            .filter(
                TokenRecuperacaoSenha.funcionario_id == funcionario_id,
                TokenRecuperacaoSenha.usado_em.is_(None),
            )
            .all()
        )
        for token in tokens:
            token.usado_em = agora
