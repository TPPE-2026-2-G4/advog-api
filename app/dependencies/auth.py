from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.funcionario import Funcionario
from app.utils.seguranca import extrair_funcionario_id_do_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def obter_funcionario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Funcionario:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        funcionario_id = extrair_funcionario_id_do_token(token)
    except ValueError as e:
        raise credenciais_invalidas from e

    funcionario = db.get(Funcionario, funcionario_id)
    if not funcionario:
        raise credenciais_invalidas

    return funcionario


def exigir_permissao(permissao: str):

    def verificar(
        funcionario: Funcionario = Depends(obter_funcionario_atual),
    ) -> Funcionario:
        permissoes = funcionario.cargo.permissao or {}
        if not permissoes.get(permissao, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return funcionario

    return verificar
