from pydantic import BaseModel, EmailStr, Field

from app.funcionario.schema import FuncionarioResponse


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    funcionario: FuncionarioResponse


class SolicitarRecuperacaoSenha(BaseModel):
    email: EmailStr


class RedefinirSenha(BaseModel):
    token: str = Field(..., min_length=1)
    senha: str = Field(..., min_length=8)


class MensagemResponse(BaseModel):
    mensagem: str
