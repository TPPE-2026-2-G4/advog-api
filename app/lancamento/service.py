from sqlalchemy.orm import Session

from app.lancamento.model import (
    Lancamento,
    SituacaoLancamento,
    StatusLancamento,
    TipoLancamento,
)
from app.lancamento.repository import LancamentoRepository
from app.lancamento.schema import (
    LancamentoCreate,
    LancamentoFilter,
    LancamentoResumo,
    LancamentoStatusUpdate,
    LancamentoUpdate,
    ResumoSituacao,
)


def _validar_status_para_tipo(tipo: TipoLancamento, status: StatusLancamento) -> None:
    permitidos = [StatusLancamento.PENDENTE, StatusLancamento.ATRASADO]
    permitidos.append(
        StatusLancamento.PAGO if tipo == TipoLancamento.SAIDA else StatusLancamento.RECEBIDO
    )
    if status not in permitidos:
        raise ValueError(
            f"Status '{status}' inválido para lançamento do tipo '{tipo}'. "
            f"Valores permitidos: {', '.join(permitidos)}"
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

    def buscar_por_id(self, lancamento_id: int) -> Lancamento:
        lancamento = self.repository.buscar_por_id(lancamento_id)
        if not lancamento:
            raise ValueError("Lançamento não encontrado")
        return lancamento

    def listar_lancamentos(self, filtros: LancamentoFilter) -> list[Lancamento]:
        self._validar_periodo(filtros)
        lancamentos = self.repository.buscar_por_filtros(
            inicio=filtros.inicio,
            fim=filtros.fim,
            tipo=filtros.tipo,
            categoria_id=filtros.categoria_id,
            cliente_id=filtros.cliente_id,
        )
        if filtros.situacao is not None:
            lancamentos = [item for item in lancamentos if item.situacao == filtros.situacao]
        return lancamentos

    def resumir_lancamentos(self, filtros: LancamentoFilter) -> LancamentoResumo:
        filtros.situacao = None
        resumos = {situacao: ResumoSituacao() for situacao in SituacaoLancamento}
        for item in self.listar_lancamentos(filtros):
            resumo = resumos[item.situacao]
            resumo.quantidade += 1
            if item.tipo == TipoLancamento.ENTRADA:
                resumo.total_entradas += item.valor
            else:
                resumo.total_saidas += item.valor
        return LancamentoResumo(
            inicio=filtros.inicio,
            fim=filtros.fim,
            previsto=resumos[SituacaoLancamento.PREVISTO],
            realizado=resumos[SituacaoLancamento.REALIZADO],
            atrasado=resumos[SituacaoLancamento.ATRASADO],
        )

    def criar_lancamento(self, dados: LancamentoCreate) -> Lancamento:
        _validar_status_para_tipo(dados.tipo, dados.status)
        self._validar_referencias(dados.categoria_id, dados.cliente_id)
        return self.repository.criar(Lancamento(**dados.model_dump()))

    def atualizar_lancamento(self, lancamento_id: int, dados: LancamentoUpdate) -> Lancamento:
        lancamento = self.buscar_por_id(lancamento_id)
        campos = dados.model_dump(exclude_unset=True)

        if campos.get("tipo") is not None:
            _validar_status_para_tipo(campos["tipo"], lancamento.status)
        for obrigatorio in ("titulo", "tipo", "data_vencimento", "valor"):
            if obrigatorio in campos and campos[obrigatorio] is None:
                raise ValueError(f"O campo '{obrigatorio}' não pode ser nulo")
        self._validar_referencias(campos.get("categoria_id"), campos.get("cliente_id"))

        for campo, valor in campos.items():
            setattr(lancamento, campo, valor)
        return self.repository.atualizar(lancamento)

    def atualizar_status(self, lancamento_id: int, dados: LancamentoStatusUpdate) -> Lancamento:
        lancamento = self.buscar_por_id(lancamento_id)
        _validar_status_para_tipo(lancamento.tipo, dados.status)
        lancamento.status = dados.status
        return self.repository.atualizar(lancamento)

    def deletar_lancamento(self, lancamento_id: int) -> None:
        self.repository.deletar(self.buscar_por_id(lancamento_id))
