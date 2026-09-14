from sqlalchemy.orm import Session

from app.models.cargo import Cargo
from app.repositories.cargo import CargoRepository
from app.schemas.cargo import CargoCreate, CargoUpdate


class CargoService:
    def __init__(self, db_session: Session):
        self.repository = CargoRepository(db_session)

    def buscar_todos(self) -> list[Cargo]:
        return self.repository.buscar_todos()

    def buscar_por_id(self, cargo_id: int) -> Cargo:
        cargo = self.repository.buscar_por_id(cargo_id)
        if not cargo:
            raise ValueError("Cargo não encontrado")
        return cargo

    def criar_cargo(self, dados: CargoCreate) -> Cargo:
        if self.repository.buscar_por_nome(dados.nome_cargo):
            raise ValueError("Cargo já cadastrado")

        cargo = Cargo(**dados.model_dump(exclude_unset=True))
        return self.repository.criar(cargo)

    def atualizar_cargo(self, cargo_id: int, dados: CargoUpdate) -> Cargo:
        cargo = self.buscar_por_id(cargo_id)
        dados_enviados = dados.model_dump(exclude_unset=True)

        if dados.nome_cargo is not None and dados.nome_cargo != cargo.nome_cargo:
            if self.repository.buscar_por_nome(dados.nome_cargo):
                raise ValueError("Cargo já cadastrado")
            cargo.nome_cargo = dados.nome_cargo

        if "descricao" in dados_enviados:
            cargo.descricao = dados.descricao

        if dados.permissao is not None:
            cargo.permissao = dados.permissao.model_dump()

        return self.repository.atualizar(cargo)

    def deletar_cargo(self, cargo_id: int) -> Cargo:
        cargo = self.buscar_por_id(cargo_id)

        if cargo.funcionarios:
            raise ValueError("Não é possível excluir um cargo associado a funcionários")

        return self.repository.deletar(cargo)
