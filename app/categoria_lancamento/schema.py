from pydantic import BaseModel, ConfigDict, Field


class CategoriaLancamentoBase(BaseModel):
    nome_categoria: str = Field(min_length=1, max_length=100)


class CategoriaLancamentoCreate(CategoriaLancamentoBase):
    pass


class CategoriaLancamentoUpdate(CategoriaLancamentoBase):
    pass


class CategoriaLancamentoResponse(CategoriaLancamentoBase):
    categoria_id: int

    model_config = ConfigDict(from_attributes=True)
