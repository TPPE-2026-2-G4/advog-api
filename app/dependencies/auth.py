from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.funcionario import Funcionario
from app.utils.seguranca import decodificar_token

security = HTTPBearer()


def obter_funcionario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Funcionario:
    try:
        payload = decodificar_token(credentials.credentials)
        funcionario_id_raw = payload.get("sub")
        if funcionario_id_raw is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        funcionario_id = int(funcionario_id_raw)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado"
        ) from e

    funcionario = db.get(Funcionario, funcionario_id)
    if funcionario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Funcionário não encontrado"
        )

    return funcionario


def exigir_permissao(permissao: str):

    def verificar(
        funcionario: Funcionario = Depends(obter_funcionario_atual),
    ) -> Funcionario:
        permissoes = funcionario.cargo.permissao or {}  # type: ignore[attr-defined]
        if not permissoes.get(permissao, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return funcionario

    return verificar
