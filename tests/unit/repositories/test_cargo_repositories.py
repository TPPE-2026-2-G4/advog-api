from app.models.cargo import Cargo
from app.repositories.cargo import CargoRepository


def test_criar_e_buscar_cargo_por_id(db_session):
    repository = CargoRepository(db_session)
    novo_cargo = Cargo(nome_cargo="Advogado Sênior")

    cargo_criado = repository.criar(novo_cargo)

    assert cargo_criado.cargo_id is not None
    assert cargo_criado.nome_cargo == "Advogado Sênior"

    cargo_buscado = repository.buscar_por_id(cargo_criado.cargo_id)
    assert cargo_buscado is not None
    assert cargo_buscado.nome_cargo == "Advogado Sênior"


def test_buscar_cargo_por_nome(db_session):
    repository = CargoRepository(db_session)
    cargo = Cargo(nome_cargo="Assistente Jurídico")
    repository.criar(cargo)

    encontrado = repository.buscar_por_nome("Assistente Jurídico")
    assert encontrado is not None
    assert encontrado.nome_cargo == "Assistente Jurídico"


def test_buscar_todos_cargos(db_session):
    repository = CargoRepository(db_session)
    repository.criar(Cargo(nome_cargo="Cargo 1"))
    repository.criar(Cargo(nome_cargo="Cargo 2"))

    todos = repository.buscar_todos()
    assert len(todos) >= 2
