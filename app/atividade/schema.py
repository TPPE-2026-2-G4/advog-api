from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ResponsavelKanbanResponse(BaseModel):
    funcionario_id: int
    nome: str

    model_config = ConfigDict(from_attributes=True)


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


def _validar_periodo(
    data_inicio: datetime | None, data_prazo: datetime | None, data_realizado: datetime | None
) -> None:
    if data_inicio and data_prazo and data_prazo < data_inicio:
        raise ValueError("data_prazo não pode ser anterior a data_inicio")
    if data_inicio and data_realizado and data_realizado < data_inicio:
        raise ValueError("data_realizado não pode ser anterior a data_inicio")


class AtividadeCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=100)
    descricao: str = Field(min_length=1, max_length=255)
    data_inicio: datetime
    data_prazo: datetime
    data_realizado: datetime | None = None
    etapa_id: int
    processo_id: int | None = None
    responsaveis_ids: list[int] = Field(
        default_factory=list, description="Funcionários responsáveis pela atividade."
    )

    @field_validator("responsaveis_ids")
    @classmethod
    def remover_responsaveis_duplicados(cls, ids: list[int]) -> list[int]:
        return list(dict.fromkeys(ids))

    @model_validator(mode="after")
    def validar_periodo(self):
        _validar_periodo(self.data_inicio, self.data_prazo, self.data_realizado)
        return self


class AtividadeUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=100)
    descricao: str | None = Field(default=None, min_length=1, max_length=255)
    data_inicio: datetime | None = None
    data_prazo: datetime | None = None
    data_realizado: datetime | None = None
    etapa_id: int | None = None
    processo_id: int | None = None
    responsaveis_ids: list[int] | None = Field(
        default=None,
        description="Quando informado, substitui por completo a lista de responsáveis.",
    )

    @field_validator("responsaveis_ids")
    @classmethod
    def remover_responsaveis_duplicados(cls, ids: list[int] | None) -> list[int] | None:
        return None if ids is None else list(dict.fromkeys(ids))

    @model_validator(mode="after")
    def validar_campos_e_periodo(self):
        nulos = [
            campo
            for campo in (
                "titulo",
                "descricao",
                "data_inicio",
                "data_prazo",
                "etapa_id",
                "responsaveis_ids",
            )
            if campo in self.model_fields_set and getattr(self, campo) is None
        ]
        if nulos:
            raise ValueError(f"Campos não aceitam valor nulo: {', '.join(nulos)}")
        _validar_periodo(self.data_inicio, self.data_prazo, self.data_realizado)
        return self


class AtividadeResponse(BaseModel):
    atividade_id: int
    titulo: str
    descricao: str
    data_inicio: datetime
    data_prazo: datetime
    data_realizado: datetime | None
    etapa_id: int
    processo_id: int | None
    responsaveis: list[ResponsavelKanbanResponse] = Field(
        default_factory=list, validation_alias="funcionarios"
    )

    model_config = ConfigDict(from_attributes=True)


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
