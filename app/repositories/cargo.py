from sqlalchemy.orm import Session

from app.models.cargo import Cargo


class CargoRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def buscar_todos(self) -> list[Cargo]:
        return self.db.query(Cargo).all()

    def buscar_por_id(self, cargo_id: int) -> Cargo | None:
        return self.db.query(Cargo).filter_by(cargo_id=cargo_id).first()

    def buscar_por_nome(self, nome_cargo: str) -> Cargo | None:
        return self.db.query(Cargo).filter_by(nome_cargo=nome_cargo).first()

    def criar(self, cargo: Cargo) -> Cargo:
        self.db.add(cargo)
        self.db.commit()
        self.db.refresh(cargo)
        return cargo
