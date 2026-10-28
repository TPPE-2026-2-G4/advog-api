from pydantic import BaseModel


class TrocarResponsavelRequest(BaseModel):
    novo_funcionario_id: int
