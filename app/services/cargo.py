from sqlalchemy.orm import Session

from app.models.cargo import Cargo
from app.repositories.cargo import CargoRepository
from app.schemas.cargo import CargoCreate


class CargoService:
    def __init__(self, db_session: Session):
        self.repository = CargoRepository(db_session)

    def buscar_todos(self) -> list[Cargo]:
        return self.repository.buscar_todos()

    def criar_cargo(self, dados: CargoCreate) -> Cargo:
        if self.repository.buscar_por_nome(dados.nome_cargo):
            raise ValueError("Cargo já cadastrado")

        cargo = Cargo(nome_cargo=dados.nome_cargo)
        return self.repository.criar(cargo)
