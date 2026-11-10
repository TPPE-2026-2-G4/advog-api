from pydantic import BaseModel, ConfigDict, Field, model_validator

PERMISSOES_IMPLICADAS: dict[str, str] = {
    "gerenciar_processos": "visualizar_processos",
    "gerenciar_atividades": "visualizar_atividades",
    "gerenciar_financeiro": "visualizar_financeiro",
    "gerenciar_equipe": "visualizar_equipe",
}


class PermissaoBase(BaseModel):
    visualizar_processos: bool = False
    gerenciar_processos: bool = False
    visualizar_atividades: bool = False
    gerenciar_atividades: bool = False
    visualizar_financeiro: bool = False
    gerenciar_financeiro: bool = False
    visualizar_equipe: bool = False
    gerenciar_equipe: bool = False
    gerenciar_site: bool = False
    configuracoes_sistema: bool = False

    @model_validator(mode="after")
    def garantir_visualizacao_de_quem_gerencia(self) -> "PermissaoBase":
        for gerenciar, visualizar in PERMISSOES_IMPLICADAS.items():
            if getattr(self, gerenciar):
                setattr(self, visualizar, True)
        return self


class CargoBase(BaseModel):
    nome_cargo: str = Field(..., min_length=2, max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    permissao: PermissaoBase = Field(default_factory=PermissaoBase)


class CargoCreate(CargoBase):
    pass


class CargoUpdate(BaseModel):
    nome_cargo: str | None = Field(default=None, min_length=2, max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    permissao: PermissaoBase | None = None


class CargoResponse(CargoBase):
    cargo_id: int

    model_config = ConfigDict(from_attributes=True)
