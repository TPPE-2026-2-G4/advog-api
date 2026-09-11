from unittest.mock import MagicMock

import pytest

from app.models.cargo import Cargo
from app.repositories.cargo import CargoRepository
from app.schemas.cargo import CargoCreate, CargoUpdate, PermissaoBase
from app.services.cargo import CargoService


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def cargo_service(mock_db_session):
    service = CargoService.__new__(CargoService)
    service.repository = MagicMock(spec=CargoRepository)
    return service


def test_construtor_cria_repository_com_a_sessao_informada(mock_db_session):
    service = CargoService(mock_db_session)

    assert isinstance(service.repository, CargoRepository)
    assert service.repository.db is mock_db_session


def test_buscar_todos_retorna_lista_de_cargos(cargo_service):
    cargos_esperados = [
        Cargo(cargo_id=1, nome_cargo="Advogado"),
        Cargo(cargo_id=2, nome_cargo="Assistente Jurídico"),
    ]

    cargo_service.repository.buscar_todos.return_value = cargos_esperados

    cargos = cargo_service.buscar_todos()

    assert isinstance(cargos, list)
    assert len(cargos) == 2
    assert cargos[0].nome_cargo == "Advogado"
    assert cargos[1].nome_cargo == "Assistente Jurídico"
    cargo_service.repository.buscar_todos.assert_called_once()


def test_buscar_cargo_por_id_sucesso(cargo_service):
    cargo_mock = Cargo(cargo_id=1, nome_cargo="Advogado")
    cargo_service.repository.buscar_por_id.return_value = cargo_mock

    resultado = cargo_service.buscar_por_id(1)

    assert resultado == cargo_mock
    cargo_service.repository.buscar_por_id.assert_called_once_with(1)


def test_buscar_cargo_por_id_inexistente_erro(cargo_service):
    cargo_service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Cargo não encontrado"):
        cargo_service.buscar_por_id(999)


def test_criar_cargo_com_sucesso(cargo_service):
    cargo_service.repository.buscar_por_nome.return_value = None
    cargo_service.repository.criar.return_value = Cargo(cargo_id=1, nome_cargo="Advogado")

    dados = CargoCreate(
        nome_cargo="Advogado",
        descricao="Atuação judicial",
        permissao=PermissaoBase(),
    )

    novo_cargo = cargo_service.criar_cargo(dados)

    assert isinstance(novo_cargo, Cargo)
    assert novo_cargo.cargo_id == 1
    assert novo_cargo.nome_cargo == "Advogado"
    cargo_service.repository.buscar_por_nome.assert_called_once_with("Advogado")
    cargo_service.repository.criar.assert_called_once()


def test_criar_cargo_com_nome_duplicado_gera_erro(cargo_service):
    cargo_service.repository.buscar_por_nome.return_value = Cargo(cargo_id=1, nome_cargo="Advogado")

    with pytest.raises(ValueError, match="Cargo já cadastrado"):
        cargo_service.criar_cargo(CargoCreate(nome_cargo="Advogado"))


def test_atualizar_cargo_sucesso(cargo_service):
    cargo_existente = Cargo(
        cargo_id=1,
        nome_cargo="Advogado Junior",
        descricao="Descrição antiga",
        permissao={},
    )
    cargo_service.repository.buscar_por_id.return_value = cargo_existente
    cargo_service.repository.buscar_por_nome.return_value = None
    cargo_service.repository.atualizar.side_effect = lambda c: c

    novas_permissoes = PermissaoBase(visualizar_processos=True)
    dados_update = CargoUpdate(
        nome_cargo="Advogado Senior",
        descricao="Nova descrição",
        permissao=novas_permissoes,
    )

    resultado = cargo_service.atualizar_cargo(1, dados_update)

    assert resultado.nome_cargo == "Advogado Senior"
    assert resultado.descricao == "Nova descrição"
    assert resultado.permissao == novas_permissoes.model_dump()
    cargo_service.repository.atualizar.assert_called_once_with(cargo_existente)


def test_atualizar_cargo_nome_duplicado_lanca_excecao(cargo_service):
    cargo_existente = Cargo(cargo_id=1, nome_cargo="Advogado Junior")
    outro_cargo = Cargo(cargo_id=2, nome_cargo="Advogado Senior")

    cargo_service.repository.buscar_por_id.return_value = cargo_existente
    cargo_service.repository.buscar_por_nome.return_value = outro_cargo

    dados_update = CargoUpdate(nome_cargo="Advogado Senior")

    with pytest.raises(ValueError, match="Cargo já cadastrado"):
        cargo_service.atualizar_cargo(1, dados_update)


def test_deletar_cargo_com_funcionarios_vinculados_lanca_excecao(cargo_service):
    cargo_com_funcionarios = Cargo(cargo_id=1, nome_cargo="Advogado")
    cargo_com_funcionarios.funcionarios = [MagicMock()]

    cargo_service.repository.buscar_por_id.return_value = cargo_com_funcionarios

    with pytest.raises(
        ValueError, match="Não é possível excluir um cargo associado a funcionários"
    ):
        cargo_service.deletar_cargo(1)

    cargo_service.repository.deletar.assert_not_called()


def test_deletar_cargo_sucesso(cargo_service):
    cargo_sem_funcionarios = Cargo(cargo_id=1, nome_cargo="Estagiário")
    cargo_sem_funcionarios.funcionarios = []

    cargo_service.repository.buscar_por_id.return_value = cargo_sem_funcionarios
    cargo_service.repository.deletar.return_value = cargo_sem_funcionarios

    resultado = cargo_service.deletar_cargo(1)

    assert resultado == cargo_sem_funcionarios

    cargo_service.repository.deletar.assert_called_once_with(cargo_sem_funcionarios)
