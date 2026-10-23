import urllib.parse
from datetime import date, datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento
from app.lancamento.repository import LancamentoRepository
from app.lancamento.schema import (
    LancamentoCalendarioResponse,
    LancamentoCreate,
    LancamentoFilter,
    LancamentoPaginadoResponse,
    LancamentoResponse,
    LancamentoResumo,
    LancamentoUpdate,
    ResumoStatus,
)


class FormatadorEventoCalendario:
    @staticmethod
    def obter_rotulo_tipo(tipo: TipoLancamento) -> str:
        return "Entrada" if tipo == TipoLancamento.ENTRADA else "Saída"

    @staticmethod
    def construir_titulo(lancamento: Lancamento) -> str:
        rotulo = FormatadorEventoCalendario.obter_rotulo_tipo(lancamento.tipo)
        return f"[{rotulo}] {lancamento.titulo} - R$ {lancamento.valor:.2f}"

    @staticmethod
    def construir_descricao(lancamento: Lancamento) -> str:
        rotulo = FormatadorEventoCalendario.obter_rotulo_tipo(lancamento.tipo)
        data_formatada = lancamento.data_vencimento.strftime("%d/%m/%Y")

        detalhes = [
            f"Tipo: {rotulo}",
            f"Valor: R$ {lancamento.valor:.2f}",
            f"Status: {lancamento.status.value}",
            f"Vencimento: {data_formatada}",
        ]
        if lancamento.descricao:
            detalhes.append(f"Descrição: {lancamento.descricao}")

        return "\n".join(detalhes)


class GeradorUrlCalendario:
    URL_BASE_GOOGLE = "https://calendar.google.com/calendar/render"
    URL_BASE_OUTLOOK = "https://outlook.office.com/calendar/0/deeplink/compose"

    @classmethod
    def gerar_url_google_calendar(cls, lancamento: Lancamento) -> str:
        data_str = lancamento.data_vencimento.strftime("%Y%m%d")

        parametros = {
            "action": "TEMPLATE",
            "text": FormatadorEventoCalendario.construir_titulo(lancamento),
            "dates": f"{data_str}/{data_str}",
            "details": FormatadorEventoCalendario.construir_descricao(lancamento),
        }
        return f"{cls.URL_BASE_GOOGLE}?{urllib.parse.urlencode(parametros)}"

    @classmethod
    def gerar_url_outlook_calendar(cls, lancamento: Lancamento) -> str:
        data_str = lancamento.data_vencimento.strftime("%Y-%m-%d")

        parametros = {
            "path": "/calendar/action/compose",
            "rru": "addevent",
            "subject": FormatadorEventoCalendario.construir_titulo(lancamento),
            "startdt": data_str,
            "enddt": data_str,
            "allday": "true",
            "body": FormatadorEventoCalendario.construir_descricao(lancamento),
        }
        return f"{cls.URL_BASE_OUTLOOK}?{urllib.parse.urlencode(parametros)}"


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


class LancamentoCalendarioService:
    def __init__(self, repositorio: LancamentoRepository | Session):
        if isinstance(repositorio, Session):
            self.repositorio = LancamentoRepository(repositorio)
        else:
            self.repositorio = repositorio

    def _validar_periodo(self, filtros: LancamentoFilter) -> None:
        if not filtros.inicio or not filtros.fim:
            raise ValueError("As datas inicial e final são obrigatórias para o calendário")
        if filtros.inicio > filtros.fim:
            raise ValueError("A data inicial não pode ser posterior à data final")

    def _sincronizar_atrasos(self) -> None:
        self.repositorio.marcar_atrasados(date.today())

    def obter_calendario(self, filtros: LancamentoFilter) -> list[LancamentoCalendarioResponse]:
        self._validar_periodo(filtros)
        self._sincronizar_atrasos()

        lancamentos = self.repositorio.buscar_por_filtros(
            inicio=filtros.inicio,
            fim=filtros.fim,
            status=filtros.status,
            tipo=filtros.tipo,
            categoria_id=filtros.categoria_id,
            cliente_id=filtros.cliente_id,
        )

        return [self._construir_evento_calendario(item) for item in lancamentos]

    def exportar_icalendar(self, filtros: LancamentoFilter) -> str:
        self._validar_periodo(filtros)
        self._sincronizar_atrasos()

        lancamentos = self.repositorio.buscar_por_filtros(
            inicio=filtros.inicio,
            fim=filtros.fim,
            status=filtros.status,
            tipo=filtros.tipo,
            categoria_id=filtros.categoria_id,
            cliente_id=filtros.cliente_id,
        )

        data_carimbo_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        linhas = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Escritorio Advocacia//Lancamentos Financeiros//PT",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        for item in lancamentos:
            linhas.extend(self._gerar_evento_ical(item, data_carimbo_utc))

        linhas.append("END:VCALENDAR")
        return "\r\n".join(linhas)

    def _construir_evento_calendario(self, lancamento: Lancamento) -> LancamentoCalendarioResponse:
        google_url = GeradorUrlCalendario.gerar_url_google_calendar(lancamento)
        outlook_url = GeradorUrlCalendario.gerar_url_outlook_calendar(lancamento)
        return LancamentoCalendarioResponse(
            lancamento_id=lancamento.lancamento_id,
            titulo=lancamento.titulo,
            descricao=lancamento.descricao,
            tipo=lancamento.tipo,
            status=lancamento.status,
            data_vencimento=lancamento.data_vencimento,
            data_pagamento=lancamento.data_pagamento,
            valor=lancamento.valor,
            cliente_id=lancamento.cliente_id,
            categoria_id=lancamento.categoria_id,
            google_calendar_url=google_url,
            outlook_calendar_url=outlook_url,
        )

    def _gerar_evento_ical(self, lancamento: Lancamento, data_carimbo_utc: str) -> list[str]:
        titulo = FormatadorEventoCalendario.construir_titulo(lancamento)
        descricao = FormatadorEventoCalendario.construir_descricao(lancamento).replace("\n", "\\n")

        data_inicio = lancamento.data_vencimento.strftime("%Y%m%d")
        data_fim = (lancamento.data_vencimento + timedelta(days=1)).strftime("%Y%m%d")
        identificador_unico = f"lancamento-{lancamento.lancamento_id}@escritorio.com.br"

        return [
            "BEGIN:VEVENT",
            f"UID:{identificador_unico}",
            f"DTSTAMP:{data_carimbo_utc}",
            f"DTSTART;VALUE=DATE:{data_inicio}",
            f"DTEND;VALUE=DATE:{data_fim}",
            f"SUMMARY:{titulo}",
            f"DESCRIPTION:{descricao}",
            "END:VEVENT",
        ]
