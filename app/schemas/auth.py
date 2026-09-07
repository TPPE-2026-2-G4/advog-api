from pydantic import BaseModel, EmailStr, Field

from app.schemas.funcionario import FuncionarioResponse


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    funcionario: FuncionarioResponse
