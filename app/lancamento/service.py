from datetime import date, datetime
from math import ceil

from sqlalchemy.orm import Session

from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento
from app.lancamento.repository import LancamentoRepository
from app.lancamento.schema import (
    LancamentoCreate,
    LancamentoFilter,
    LancamentoPaginadoResponse,
    LancamentoResponse,
    LancamentoResumo,
    LancamentoUpdate,
    ResumoStatus,
)


class LancamentoService:
    def __init__(self, db: Session):
        self.repository = LancamentoRepository(db)

    def _validar_periodo(self, filtros: LancamentoFilter) -> None:
        if filtros.inicio and filtros.fim and filtros.inicio > filtros.fim:
            raise ValueError("A data inicial não pode ser posterior à data final")

    def _validar_referencias(self, categoria_id: int | None, cliente_id: int | None) -> None:
        if categoria_id is not None and not self.repository.categoria_existe(categoria_id):
            raise ValueError("Categoria não encontrada")
        if cliente_id is not None and not self.repository.cliente_existe(cliente_id):
            raise ValueError("Cliente não encontrado")

    def _sincronizar_atrasos(self) -> None:
        self.repository.marcar_atrasados(date.today())

    @staticmethod
    def _filtros(filtros: LancamentoFilter) -> dict:
        return {
            "inicio": filtros.inicio,
            "fim": filtros.fim,
            "status": filtros.status,
            "tipo": filtros.tipo,
            "categoria_id": filtros.categoria_id,
            "cliente_id": filtros.cliente_id,
        }

    def buscar_por_id(self, lancamento_id: int) -> Lancamento:
        self._sincronizar_atrasos()
        lancamento = self.repository.buscar_por_id(lancamento_id)
        if not lancamento:
            raise ValueError("Lançamento não encontrado")
        return lancamento

    def listar_lancamentos(self, filtros: LancamentoFilter) -> list[Lancamento]:
        self._validar_periodo(filtros)
        self._sincronizar_atrasos()
        return self.repository.buscar_por_filtros(**self._filtros(filtros))

    def listar_lancamentos_paginado(
        self, filtros: LancamentoFilter, page: int, page_size: int
    ) -> LancamentoPaginadoResponse:
        self._validar_periodo(filtros)
        self._sincronizar_atrasos()
        itens, total = self.repository.buscar_paginado(page, page_size, **self._filtros(filtros))
        return LancamentoPaginadoResponse(
            itens=[LancamentoResponse.model_validate(item) for item in itens],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, ceil(total / page_size)),
        )

    def resumir_lancamentos(self, filtros: LancamentoFilter) -> LancamentoResumo:
        self._validar_periodo(filtros)
        self._sincronizar_atrasos()
        filtros_sql = self._filtros(filtros) | {"status": None}
        resumos = {status: ResumoStatus() for status in StatusLancamento}
        for status, tipo, quantidade, soma in self.repository.totais_por_status_e_tipo(
            **filtros_sql
        ):
            resumo = resumos[status]
            resumo.quantidade += quantidade
            if tipo == TipoLancamento.ENTRADA:
                resumo.total_entradas += soma
            else:
                resumo.total_saidas += soma
        return LancamentoResumo(
            inicio=filtros.inicio,
            fim=filtros.fim,
            pendente=resumos[StatusLancamento.PENDENTE],
            realizado=resumos[StatusLancamento.REALIZADO],
            atrasado=resumos[StatusLancamento.ATRASADO],
        )

    def criar_lancamento(self, dados: LancamentoCreate) -> Lancamento:
        self._validar_referencias(dados.categoria_id, dados.cliente_id)
        lancamento = Lancamento(
            **dados.model_dump(),
            status=Lancamento.status_para_vencimento(dados.data_vencimento),
        )
        return self.repository.criar(lancamento)

    def atualizar_lancamento(self, lancamento_id: int, dados: LancamentoUpdate) -> Lancamento:
        lancamento = self.buscar_por_id(lancamento_id)
        campos = dados.model_dump(exclude_unset=True)

        for obrigatorio in ("titulo", "tipo", "data_vencimento", "valor"):
            if obrigatorio in campos and campos[obrigatorio] is None:
                raise ValueError(f"O campo '{obrigatorio}' não pode ser nulo")
        self._validar_referencias(campos.get("categoria_id"), campos.get("cliente_id"))

        for campo, valor in campos.items():
            setattr(lancamento, campo, valor)

        if "data_vencimento" in campos and lancamento.status != StatusLancamento.REALIZADO:
            lancamento.status = Lancamento.status_para_vencimento(lancamento.data_vencimento)
        return self.repository.atualizar(lancamento)

    def alternar_status(self, lancamento_id: int) -> Lancamento:
        lancamento = self.buscar_por_id(lancamento_id)
        if lancamento.status == StatusLancamento.REALIZADO:
            lancamento.status = Lancamento.status_para_vencimento(lancamento.data_vencimento)
            lancamento.data_pagamento = None
        else:
            lancamento.status = StatusLancamento.REALIZADO
            lancamento.data_pagamento = datetime.now()
        return self.repository.atualizar(lancamento)

    def deletar_lancamento(self, lancamento_id: int) -> None:
        self.repository.deletar(self.buscar_por_id(lancamento_id))
