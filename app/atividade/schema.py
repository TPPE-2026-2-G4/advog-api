from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ProdutividadeResponse(BaseModel):
    funcionario_id: int
    nome: str
    finalizadas: int
    em_andamento: int
    a_fazer: int
    atrasadas: int
    progresso: float


class AtividadeResponse(BaseModel):
    atividade_id: int
    titulo: str
    descricao: str
    data_inicio: datetime
    data_prazo: datetime
    data_realizado: datetime | None = None
    etapa_id: int
    processo_id: int | None = None
    responsaveis: list[ResponsavelKanbanResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AtividadeFilter(BaseModel):
    atividade_id: int | None = Field(None, description="Filtrar por ID da atividade")
    titulo: str | None = Field(None, max_length=100, description="Filtrar por título da atividade")
    descricao: str | None = Field(None, max_length=255, description="Filtrar por descrição")
    etapa_id: int | None = Field(None, description="Filtrar por ID da etapa do Kanban")
    processo_id: int | None = Field(None, description="Filtrar por ID do processo vinculado")
    funcionario_id: int | None = Field(
        None, description="Filtrar por ID do funcionário responsável"
    )
    prazo_inicio: date | None = Field(None, description="Prazo a partir de (inclusive)")
    prazo_fim: date | None = Field(None, description="Prazo até (inclusive)")
    data_inicio_de: date | None = Field(None, description="Data de início a partir de (inclusive)")
    data_inicio_ate: date | None = Field(None, description="Data de início até (inclusive)")
    realizada: bool | None = Field(None, description="Filtrar por status de conclusão")
    atrasada: bool | None = Field(None, description="Filtrar por atividades atrasadas")
    apenas_minhas: bool = Field(False, description="Filtrar apenas atividades do usuário logado")
    busca_textual: str | None = Field(
        None, description="Buscar em título, descrição, processo ou responsável"
    )

    @model_validator(mode="after")
    def validar_intervalos_de_datas(self) -> "AtividadeFilter":
        if self.prazo_inicio and self.prazo_fim and self.prazo_inicio > self.prazo_fim:
            raise ValueError("prazo_inicio não pode ser posterior a prazo_fim")
        if (
            self.data_inicio_de
            and self.data_inicio_ate
            and self.data_inicio_de > self.data_inicio_ate
        ):
            raise ValueError("data_inicio_de não pode ser posterior a data_inicio_ate")
        return self
