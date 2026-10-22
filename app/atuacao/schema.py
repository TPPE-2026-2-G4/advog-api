from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class AtuacaoBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome: str = Field(
        ...,
        min_length=2,
        max_length=100,
        validation_alias=AliasChoices("nome", "titulo"),
    )
    descricao: str = Field(..., min_length=2, max_length=255)
    exibicao_institucional: bool = Field(default=True, alias="exibicaoInstitucional")


class AtuacaoCreate(AtuacaoBase):
    pass


class AtuacaoUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        validation_alias=AliasChoices("nome", "titulo"),
    )
    descricao: str | None = Field(default=None, min_length=2, max_length=255)
    exibicao_institucional: bool | None = Field(default=None, alias="exibicaoInstitucional")


class AtuacaoMudarExibicao(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    exibicao_institucional: bool = Field(..., alias="exibicaoInstitucional")


class AtuacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    atuacao_id: int
    nome: str
    titulo: str
    descricao: str
    exibicao_institucional: bool = Field(default=True, alias="exibicaoInstitucional")
