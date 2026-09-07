from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CargoBase(BaseModel):
    nome_cargo: str = Field(..., min_length=2, max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    permissao: dict[str, Any] | list[Any] | None = None


class CargoCreate(CargoBase):
    pass


class CargoUpdate(BaseModel):
    nome_cargo: str | None = Field(default=None, min_length=2, max_length=100)
    descricao: str | None = Field(default=None, max_length=255)
    permissao: dict[str, Any] | list[Any] | None = None


class CargoResponse(CargoBase):
    cargo_id: int

    model_config = ConfigDict(from_attributes=True)
