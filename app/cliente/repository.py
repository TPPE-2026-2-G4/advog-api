from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.cliente.model import Cliente
from app.cliente.schema import ClienteCreate


class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, cliente_id: int) -> Cliente | None:
        return self.db.query(Cliente).filter(Cliente.cliente_id == cliente_id).first()

    def find_all_by_filters(
        self,
        busca: str | None = None,
        responsavel_id: int | None = None,
        etapa_id: int | None = None,
    ) -> list[Cliente]:
        query = self.db.query(Cliente)

        if busca:
            query = query.filter(
                or_(
                    Cliente.nome.ilike(f"%{busca}%"),
                    Cliente.email.ilike(f"%{busca}%"),
                )
            )

        if responsavel_id is not None:
            query = query.filter(Cliente.responsavel_id == responsavel_id)

        if etapa_id is not None:
            query = query.filter(Cliente.etapa_id == etapa_id)

        return query.all()

    def create(self, cliente_data: ClienteCreate) -> Cliente:
        novo_cliente = Cliente(**cliente_data.model_dump())
        self.db.add(novo_cliente)
        self.db.commit()
        self.db.refresh(novo_cliente)
        return novo_cliente

    def update(self, cliente_id: int, cliente_data: dict) -> Cliente | None:
        cliente = self.get_by_id(cliente_id)
        if not cliente:
            return None

        for key, value in cliente_data.items():
            setattr(cliente, key, value)

        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def delete(self, cliente_id: int) -> bool:
        cliente = self.get_by_id(cliente_id)
        if not cliente:
            return False

        self.db.delete(cliente)
        self.db.commit()
        return True
