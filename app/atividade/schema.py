from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResponsavelKanbanResponse(BaseModel):
    funcionario_id: int
    nome: str


class AtividadeKanbanResponse(BaseModel):
    atividade_id: int
    titulo: str
    data_prazo: datetime
    processo_id: int | None
    responsaveis: list[ResponsavelKanbanResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EtapaKanbanResponse(BaseModel):
    etapa_id: int
    nome: str
    ordem: int
    atividades: list[AtividadeKanbanResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class KanbanResponse(BaseModel):
    escopo: Literal["usuario", "escritorio"] = Field(
        description="usuario: Minhas atividades; escritorio: Atividades do escritório."
    )
    etapas: list[EtapaKanbanResponse]
