from typing import Literal

from pydantic import BaseModel, Field


class ResumoAtividadesResponse(BaseModel):
    escopo: Literal["usuario", "escritorio"] = Field(
        description="usuario: Minhas atividades; escritorio: Atividades do escritório."
    )
    pendentes: int = Field(ge=0)
    em_execucao: int = Field(ge=0)
    concluidas: int = Field(ge=0)
    atrasadas: int = Field(ge=0)
