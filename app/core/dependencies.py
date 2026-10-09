from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.seguranca import extrair_funcionario_id_do_token
from app.funcionario.model import Funcionario

bearer_scheme = HTTPBearer(auto_error=False)


def obter_funcionario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Funcionario:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credenciais is None:
        raise credenciais_invalidas

    try:
        funcionario_id = extrair_funcionario_id_do_token(credenciais.credentials)
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
