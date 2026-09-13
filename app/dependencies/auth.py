from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.funcionario import Funcionario
from app.utils.seguranca import decodificar_token

security = HTTPBearer()


def get_current_funcionario(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Funcionario:

    try:
        payload = decodificar_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado"
        ) from e

    funcionario_id = payload.get("sub")
    if funcionario_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    funcionario = db.get(Funcionario, int(funcionario_id))
    if funcionario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Funcionário não encontrado"
        )

    return funcionario


def exigir_permissao(permissao: str):

    def verificar(
        funcionario: Funcionario = Depends(get_current_funcionario),
    ) -> Funcionario:
        permissoes = funcionario.cargo.permissao or {}  # type: ignore[attr-defined]
        if not permissoes.get(permissao, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return funcionario

    return verificar
