from sqlalchemy.orm import Session

from app.cliente.model import Cliente
from app.cliente.repository import ClienteRepository
from app.cliente.schema import ClienteCreate, ClienteFilter, ClienteUpdate


class ClienteNaoEncontradoError(Exception):
    pass


class ClienteService:
    def __init__(self, db: Session):
        self.repository = ClienteRepository(db)

    def search_clientes(self, filters: ClienteFilter) -> list[Cliente]:
        return self.repository.find_all_by_filters(
            busca=filters.busca,
            responsavel_id=filters.responsavel_id,
            etapa_id=filters.etapa_id,
        )

    def create_cliente(self, cliente_data: ClienteCreate) -> Cliente:
        return self.repository.create(cliente_data)

    def get_cliente_by_id(self, cliente_id: int) -> Cliente:
        cliente = self.repository.get_by_id(cliente_id)
        if not cliente:
            raise ClienteNaoEncontradoError("Cliente não encontrado")
        return cliente

    def update_cliente(self, cliente_id: int, cliente_data: ClienteUpdate) -> Cliente:
        cliente = self.repository.update(cliente_id, cliente_data.model_dump(exclude_unset=True))
        if not cliente:
            raise ClienteNaoEncontradoError("Cliente não encontrado")
        return cliente

    def delete_cliente(self, cliente_id: int) -> bool:
        sucesso = self.repository.delete(cliente_id)
        if not sucesso:
            raise ClienteNaoEncontradoError("Cliente não encontrado")
        return sucesso
