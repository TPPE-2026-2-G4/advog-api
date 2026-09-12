from pydantic import BaseModel, ConfigDict, Field


class PermissaoBase(BaseModel):
    criar_processos: bool = False
    editar_processos: bool = False
    excluir_processos: bool = False
    visualizar_processos: bool = False
    gerenciar_financeiro: bool = False
    visualizar_financeiro: bool = False
    gerenciar_equipe: bool = False
    visualizar_equipe: bool = False
    configuracoes_sistema: bool = False


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
