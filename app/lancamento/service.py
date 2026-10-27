from datetime import date, datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from app.core.relatorio import (
    LIMITE_LINHAS,
    Arquivo,
    Coluna,
    FormatoRelatorio,
    Tabela,
    TipoColuna,
    gerar_arquivo,
)
from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento
from app.lancamento.repository import LancamentoRepository
from app.lancamento.schema import (
    LancamentoCreate,
    LancamentoFilter,
    LancamentoGrafico,
    LancamentoPaginadoResponse,
    LancamentoResponse,
    LancamentoResumo,
    LancamentoUpdate,
    PontoGrafico,
    ResumoStatus,
)


class LancamentoService:
    def __init__(self, db: Session):
        self.repository = LancamentoRepository(db)

    @staticmethod
    def _resolver_periodo(
        inicio: date | None, fim: date | None, dias: int | None
    ) -> tuple[date | None, date | None]:
        if dias is not None:
            fim = fim or date.today()
            inicio = inicio or (fim - timedelta(days=dias - 1))
        if inicio and fim and inicio > fim:
            raise ValueError("A data inicial não pode ser posterior à data final")
        return inicio, fim

    @staticmethod
    def _validar_valores(valor_min: float | None, valor_max: float | None) -> None:
        if valor_min is not None and valor_max is not None and valor_min > valor_max:
            raise ValueError("O valor mínimo não pode ser maior que o valor máximo")

    def _validar_referencias(self, categoria_id: int | None, cliente_id: int | None) -> None:
        if categoria_id is not None and not self.repository.categoria_existe(categoria_id):
            raise ValueError("Categoria não encontrada")
        if cliente_id is not None and not self.repository.cliente_existe(cliente_id):
            raise ValueError("Cliente não encontrado")

    def _sincronizar_atrasos(self) -> None:
        self.repository.marcar_atrasados(date.today())

    def _preparar_filtros(self, filtros: LancamentoFilter) -> dict:
        inicio, fim = self._resolver_periodo(filtros.inicio, filtros.fim, filtros.dias)
        self._validar_valores(filtros.valor_min, filtros.valor_max)
        self._sincronizar_atrasos()
        return {
            "inicio": inicio,
            "fim": fim,
            "status": filtros.status,
            "tipo": filtros.tipo,
            "categoria_id": filtros.categoria_id,
            "cliente_id": filtros.cliente_id,
            "valor_min": filtros.valor_min,
            "valor_max": filtros.valor_max,
        }

    def buscar_por_id(self, lancamento_id: int) -> Lancamento:
        self._sincronizar_atrasos()
        lancamento = self.repository.buscar_por_id(lancamento_id)
        if not lancamento:
            raise ValueError("Lançamento não encontrado")
        return lancamento

    def listar_lancamentos(self, filtros: LancamentoFilter) -> list[Lancamento]:
        return self.repository.buscar_por_filtros(**self._preparar_filtros(filtros))

    def listar_lancamentos_paginado(
        self, filtros: LancamentoFilter, page: int, page_size: int
    ) -> LancamentoPaginadoResponse:
        itens, total = self.repository.buscar_paginado(
            page, page_size, **self._preparar_filtros(filtros)
        )
        return LancamentoPaginadoResponse(
            itens=[LancamentoResponse.model_validate(item) for item in itens],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, ceil(total / page_size)),
        )

    def exportar_lancamentos(self, filtros: LancamentoFilter, formato: FormatoRelatorio) -> Arquivo:
        lancamentos = self.repository.buscar_para_exportacao(
            LIMITE_LINHAS + 1, **self._preparar_filtros(filtros)
        )
        if len(lancamentos) > LIMITE_LINHAS:
            raise ValueError(
                f"A exportação excede {LIMITE_LINHAS} lançamentos; "
                "refine os filtros e tente novamente"
            )
        clientes = self.repository.buscar_nomes_clientes(
            {item.cliente_id for item in lancamentos if item.cliente_id is not None}
        )
        entradas = sum(i.valor for i in lancamentos if i.tipo == TipoLancamento.ENTRADA)
        saidas = sum(i.valor for i in lancamentos if i.tipo == TipoLancamento.SAIDA)
        tabela = Tabela(
            titulo="Relatório de Lançamentos",
            colunas=[
                Coluna("Título"),
                Coluna("Descrição"),
                Coluna("Tipo"),
                Coluna("Status"),
                Coluna("Categoria"),
                Coluna("Cliente"),
                Coluna("Vencimento", TipoColuna.DATA),
                Coluna("Pagamento", TipoColuna.DATA),
                Coluna("Valor", TipoColuna.MOEDA),
            ],
            linhas=[
                [
                    item.titulo,
                    item.descricao,
                    "Entrada" if item.tipo == TipoLancamento.ENTRADA else "Saída",
                    item.status.value,
                    item.categoria_lancamento.nome_categoria if item.categoria_lancamento else None,
                    clientes.get(item.cliente_id) if item.cliente_id is not None else None,
                    item.data_vencimento,
                    item.data_pagamento,
                    item.valor,
                ]
                for item in lancamentos
            ],
            resumo=[
                ("Total de entradas", float(entradas)),
                ("Total de saídas", float(saidas)),
                ("Saldo", float(entradas - saidas)),
            ],
        )
        return gerar_arquivo(tabela, formato)

    def resumir_lancamentos(self, filtros: LancamentoFilter) -> LancamentoResumo:
        filtros_sql = self._preparar_filtros(filtros) | {"status": None}
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
            inicio=filtros_sql["inicio"],
            fim=filtros_sql["fim"],
            pendente=resumos[StatusLancamento.PENDENTE],
            realizado=resumos[StatusLancamento.REALIZADO],
            atrasado=resumos[StatusLancamento.ATRASADO],
        )

    def gerar_grafico(self, filtros: LancamentoFilter) -> LancamentoGrafico:
        filtros_sql = self._preparar_filtros(filtros)
        pontos: dict[date, PontoGrafico] = {}
        total_entradas = 0.0
        total_saidas = 0.0

        for dia_raw, tipo, quantidade, soma in self.repository.totais_por_dia_e_tipo(**filtros_sql):
            dia = date.fromisoformat(str(dia_raw))
            ponto = pontos.setdefault(dia, PontoGrafico(data=dia))
            ponto.quantidade += quantidade
            if tipo == TipoLancamento.ENTRADA:
                ponto.total_entradas += soma
                total_entradas += soma
            else:
                ponto.total_saidas += soma
                total_saidas += soma
            ponto.saldo = ponto.total_entradas - ponto.total_saidas

        return LancamentoGrafico(
            inicio=filtros_sql["inicio"],
            fim=filtros_sql["fim"],
            valor_min=filtros.valor_min,
            valor_max=filtros.valor_max,
            total_entradas=total_entradas,
            total_saidas=total_saidas,
            saldo=total_entradas - total_saidas,
            itens=list(pontos.values()),
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
