from unittest.mock import MagicMock

import pytest

from app.models.cargo import Cargo
from app.repositories.cargo import CargoRepository
from app.schemas.cargo import CargoCreate
from app.services.cargo import CargoService


def test_criar_cargo_com_sucesso():
    service = CargoService.__new__(CargoService)
    service.repository = MagicMock(spec=CargoRepository)
    service.repository.buscar_por_nome.return_value = None
    service.repository.criar.return_value = Cargo(cargo_id=1, nome_cargo="Advogado")

    novo_cargo = service.criar_cargo(CargoCreate(nome_cargo="Advogado"))

    assert isinstance(novo_cargo, Cargo)
    assert novo_cargo.cargo_id == 1
    assert novo_cargo.nome_cargo == "Advogado"


def test_criar_cargo_com_nome_duplicado_gera_erro():
    service = CargoService.__new__(CargoService)
    service.repository = MagicMock(spec=CargoRepository)
    service.repository.buscar_por_nome.return_value = Cargo(cargo_id=1, nome_cargo="Advogado")

    with pytest.raises(ValueError, match="Cargo já cadastrado"):
        service.criar_cargo(CargoCreate(nome_cargo="Advogado"))


def test_buscar_todos_retorn_lista_de_cargos():
    service = CargoService.__new__(CargoService)
    service.repository = MagicMock(spec=CargoRepository)
    service.repository.buscar_todos.return_value = [
        Cargo(cargo_id=1, nome_cargo="Advogado"),
        Cargo(cargo_id=2, nome_cargo="Assistente Jurídico"),
    ]

    cargos = service.buscar_todos()

    assert isinstance(cargos, list)
    assert len(cargos) == 2
    assert cargos[0].nome_cargo == "Advogado"
    assert cargos[1].nome_cargo == "Assistente Jurídico"


def test_construtor_cria_repository_com_a_sessao_informada(db_session):
    service = CargoService(db_session)

    assert isinstance(service.repository, CargoRepository)
    assert service.repository.db is db_session
