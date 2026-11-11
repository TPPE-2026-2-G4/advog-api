import re
from datetime import UTC, datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.cliente.model import Cliente
from app.cliente.schema import ClienteCreate

BUSCA_DOCUMENTO_REGEX = re.compile(r"^[\d.\-/\s]+$")


def _documento_somente_digitos():
    expressao = Cliente.documento
    for separador in (".", "-", "/", " "):
        expressao = func.replace(expressao, separador, "")
    return expressao


class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, cliente_id: int) -> Cliente | None:
        return self.db.query(Cliente).filter(Cliente.cliente_id == cliente_id).first()

    def _build_query(
        self,
        busca: str | None = None,
        responsavel_id: int | None = None,
        etapa_id: int | None = None,
    ):
        query = self.db.query(Cliente)

        if busca:
            condicoes = [
                Cliente.nome.ilike(f"%{busca}%"),
                Cliente.email.ilike(f"%{busca}%"),
                Cliente.documento.ilike(f"%{busca}%"),
            ]
            # Documentos são salvos com a máscara digitada (ex.: 123.456.789-00); uma busca
            # que parece CPF/CNPJ deve casar independentemente da pontuação.
            if BUSCA_DOCUMENTO_REGEX.match(busca):
                digitos = re.sub(r"\D", "", busca)
                if digitos:
                    condicoes.append(_documento_somente_digitos().ilike(f"%{digitos}%"))
            query = query.filter(or_(*condicoes))

        if responsavel_id is not None:
            query = query.filter(Cliente.responsavel_id == responsavel_id)

        if etapa_id is not None:
            query = query.filter(Cliente.etapa_id == etapa_id)

        return query

    def find_all_by_filters(
        self,
        busca: str | None = None,
        responsavel_id: int | None = None,
        etapa_id: int | None = None,
    ) -> list[Cliente]:
        return self._build_query(busca, responsavel_id, etapa_id).all()

    def find_paginated_by_filters(
        self,
        page: int,
        page_size: int,
        busca: str | None = None,
        responsavel_id: int | None = None,
        etapa_id: int | None = None,
    ) -> tuple[list[Cliente], int]:
        query = self._build_query(busca, responsavel_id, etapa_id)
        total = query.count()
        itens = (
            query.order_by(Cliente.cliente_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return itens, total

    def create(self, cliente_data: ClienteCreate) -> Cliente:
        dados = cliente_data.model_dump()
        dados["ultima_interacao"] = dados["ultima_interacao"] or datetime.now(UTC)
        novo_cliente = Cliente(**dados)
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
