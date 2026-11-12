from math import ceil

from sqlalchemy.orm import Session

from app.cliente.model import Cliente
from app.cliente.repository import ClienteRepository
from app.cliente.schema import (
    ClienteCreate,
    ClienteFilter,
    ClientePaginadoFilter,
    ClientePaginadoResponse,
    ClienteResponse,
    ClienteUpdate,
)
from app.notificacao.eventos import NotificacaoEventos


class ClienteNaoEncontradoError(Exception):
    pass


class ClienteService:
    def __init__(self, db: Session):
        self.repository = ClienteRepository(db)
        self.eventos = NotificacaoEventos(db)

    def search_clientes(self, filters: ClienteFilter) -> list[Cliente]:
        return self.repository.find_all_by_filters(
            busca=filters.busca,
            responsavel_id=filters.responsavel_id,
            etapa_id=filters.etapa_id,
        )

    def search_clientes_paginado(self, filters: ClientePaginadoFilter) -> ClientePaginadoResponse:
        itens, total = self.repository.find_paginated_by_filters(
            page=filters.page,
            page_size=filters.page_size,
            busca=filters.busca,
            responsavel_id=filters.responsavel_id,
            etapa_id=filters.etapa_id,
        )
        return ClientePaginadoResponse(
            itens=[ClienteResponse.model_validate(cliente) for cliente in itens],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=max(1, ceil(total / filters.page_size)),
        )

    def create_cliente(self, cliente_data: ClienteCreate) -> Cliente:
        cliente = self.repository.create(cliente_data)
        self.eventos.cliente_criado(cliente)
        return cliente

    def get_cliente_by_id(self, cliente_id: int) -> Cliente:
        cliente = self.repository.get_by_id(cliente_id)
        if not cliente:
            raise ClienteNaoEncontradoError("Cliente não encontrado")
        return cliente

    def update_cliente(
        self, cliente_id: int, cliente_data: ClienteUpdate, ator_id: int | None = None
    ) -> Cliente:
        existente = self.repository.get_by_id(cliente_id)
        responsavel_anterior = existente.responsavel_id if existente else None
        cliente = self.repository.update(cliente_id, cliente_data.model_dump(exclude_unset=True))
        if not cliente:
            raise ClienteNaoEncontradoError("Cliente não encontrado")
        if cliente.responsavel_id is not None and cliente.responsavel_id != responsavel_anterior:
            self.eventos.cliente_atribuido(cliente, ator_id)
        return cliente

    def delete_cliente(self, cliente_id: int) -> bool:
        sucesso = self.repository.delete(cliente_id)
        if not sucesso:
            raise ClienteNaoEncontradoError("Cliente não encontrado")
        return sucesso
