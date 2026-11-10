from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.cargo.schema import PermissaoBase
from app.config.database import get_db
from app.core.permissoes import PERMISSOES_IMPLICADAS
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


def _concede(permissoes: dict, permissao: str) -> bool:
    if permissoes.get(permissao, False):
        return True
    return any(
        permissoes.get(gerenciar, False)
        for gerenciar, visualizar in PERMISSOES_IMPLICADAS.items()
        if visualizar == permissao
    )


def exigir_permissao(*permissoes_aceitas: str):
    """Exige que o cargo tenha ao menos UMA das permissões informadas (ou quem a inclui)."""
    desconhecidas = set(permissoes_aceitas) - set(PermissaoBase.model_fields)
    if desconhecidas:
        raise ValueError(f"Permissão inexistente em exigir_permissao: {sorted(desconhecidas)}")

    def verificar(
        funcionario: Funcionario = Depends(obter_funcionario_atual),
    ) -> Funcionario:
        permissoes = funcionario.cargo.permissao or {}
        if not any(_concede(permissoes, aceita) for aceita in permissoes_aceitas):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return funcionario

    return verificar
