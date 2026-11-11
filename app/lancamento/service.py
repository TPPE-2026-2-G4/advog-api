import urllib.parse
from calendar import monthrange
from datetime import date, datetime, timedelta
from itertools import islice
from math import ceil
from uuid import uuid4

from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrulestr
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
    LancamentoCalendarioResponse,
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

MAX_OCORRENCIAS = 1100
DIAS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def datas_recorrentes(regra: str, inicio: datetime) -> list[datetime]:
    """Expande apenas as frequências do formulário, dentro da janela de três anos."""
    inicio = inicio.replace(tzinfo=None)
    try:
        pares = [parte.split("=") for parte in regra.split(";")]
        campos = dict(pares)
        permitidos = {
            "FREQ",
            "INTERVAL",
            "BYDAY",
            "BYMONTHDAY",
            "BYMONTH",
            "BYSETPOS",
            "COUNT",
            "UNTIL",
        }
        if len(pares) != len(campos) or campos.keys() - permitidos:
            raise ValueError
        if campos.get("FREQ") not in {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}:
            raise ValueError
        if "BYDAY" in campos and not set(campos["BYDAY"].split(",")) <= set(DIAS):
            raise ValueError
        for campo, minimo, maximo in (
            ("BYMONTH", 1, 12),
            ("BYMONTHDAY", -31, 31),
            ("BYSETPOS", -5, 5),
        ):
            if campo in campos and any(
                not minimo <= int(v) <= maximo or int(v) == 0 for v in campos[campo].split(",")
            ):
                raise ValueError
        if not 1 <= int(campos.get("INTERVAL", "1")) <= MAX_OCORRENCIAS:
            raise ValueError
        quantidade = int(campos.get("COUNT", str(MAX_OCORRENCIAS)))
        if quantidade < 1 or ("COUNT" in campos and "UNTIL" in campos):
            raise ValueError
        if "UNTIL" in campos and datetime.strptime(campos["UNTIL"], "%Y%m%dT%H%M%S") < inicio:
            raise ValueError
        # O primeiro vencimento conta mesmo quando não pertence aos dias selecionados.
        campos.pop("COUNT", None)
        campos["UNTIL"] = min(
            datetime.strptime(campos.get("UNTIL", "99991231T235959"), "%Y%m%dT%H%M%S"),
            inicio + relativedelta(years=3),
        ).strftime("%Y%m%dT%H%M%S")
        recorrencia = rrulestr(";".join(f"{k}={v}" for k, v in campos.items()), dtstart=inicio)
        limite = min(quantidade, MAX_OCORRENCIAS)
        datas = [inicio]
        for data in islice(recorrencia, MAX_OCORRENCIAS):
            if data > inicio:
                datas.append(data)
            if len(datas) >= limite:
                break
        return datas[:limite]
    except (ValueError, TypeError, OverflowError) as e:
        raise ValueError("Regra de recorrência inválida") from e


def reancorar_regra(regra: str, anterior: datetime, novo: datetime) -> str:
    campos = dict(parte.split("=") for parte in regra.split(";"))
    # A edição redistribui apenas as ocorrências existentes, sem reiniciar COUNT/UNTIL.
    campos.pop("COUNT", None)
    campos.pop("UNTIL", None)
    frequencia = campos["FREQ"]
    if frequencia == "WEEKLY" and "BYDAY" in campos:
        dias = campos["BYDAY"].split(",")
        if set(dias) != {"MO", "TU", "WE", "TH", "FR"}:
            deslocamento = novo.weekday() - anterior.weekday()
            campos["BYDAY"] = ",".join(DIAS[(DIAS.index(d) + deslocamento) % 7] for d in dias)
    if frequencia in {"MONTHLY", "YEARLY"}:
        ultimo = monthrange(novo.year, novo.month)[1]
        if "BYSETPOS" in campos:
            campos["BYDAY"] = DIAS[novo.weekday()]
            campos["BYSETPOS"] = str(-1 if novo.day + 7 > ultimo else (novo.day - 1) // 7 + 1)
        else:
            campos["BYMONTHDAY"] = str(-1 if novo.day == ultimo else novo.day)
        if frequencia == "YEARLY":
            campos["BYMONTH"] = str(novo.month)
    return ";".join(f"{k}={v}" for k, v in campos.items())


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
        if dados.rrule:
            serie_id = str(uuid4())
            campos = dados.model_dump(exclude={"data_vencimento"})
            lancamentos = [
                Lancamento(
                    **campos,
                    serie_id=serie_id,
                    data_vencimento=data,
                    status=Lancamento.status_para_vencimento(data),
                )
                for data in datas_recorrentes(dados.rrule, dados.data_vencimento)
            ]
            return self.repository.criar_serie(lancamentos)
        lancamento = Lancamento(
            **dados.model_dump(exclude={"rrule"}),
            status=Lancamento.status_para_vencimento(dados.data_vencimento),
        )
        return self.repository.criar(lancamento)

    def atualizar_lancamento(
        self, lancamento_id: int, dados: LancamentoUpdate, alcance: str = "individual"
    ) -> Lancamento:
        lancamento = self.buscar_por_id(lancamento_id)
        campos = dados.model_dump(exclude_unset=True)

        for obrigatorio in (
            "titulo",
            "descricao",
            "tipo",
            "data_vencimento",
            "valor",
            "categoria_id",
        ):
            if obrigatorio in campos and campos[obrigatorio] is None:
                raise ValueError(f"O campo '{obrigatorio}' não pode ser nulo")
        self._validar_referencias(campos.get("categoria_id"), campos.get("cliente_id"))

        if alcance == "serie":
            self._atualizar_serie(lancamento, campos)
            return lancamento

        for campo, valor in campos.items():
            setattr(lancamento, campo, valor)

        if "data_vencimento" in campos and lancamento.status != StatusLancamento.REALIZADO:
            lancamento.status = Lancamento.status_para_vencimento(lancamento.data_vencimento)
        return self.repository.atualizar(lancamento)

    def _atualizar_serie(self, lancamento: Lancamento, campos: dict) -> None:
        if not lancamento.serie_id:
            raise ValueError("O lançamento não pertence a uma série")
        futuros = self.repository.buscar_futuros_da_serie(lancamento)
        regra = lancamento.rrule
        if not regra:
            raise ValueError("A série não possui uma regra de recorrência")
        datas = [item.data_vencimento for item in futuros]
        nova_data = campos.get("data_vencimento")
        if nova_data and nova_data.replace(tzinfo=None) != lancamento.data_vencimento:
            regra = reancorar_regra(regra, lancamento.data_vencimento, nova_data)
            datas = datas_recorrentes(f"{regra};COUNT={len(futuros)}", nova_data)
            if len(datas) != len(futuros):
                raise ValueError("Os novos vencimentos excedem o limite de três anos")
        for item, data in zip(futuros, datas, strict=True):
            if item.status == StatusLancamento.REALIZADO:
                continue
            for campo, valor in campos.items():
                if campo != "data_vencimento":
                    setattr(item, campo, valor)
            item.data_vencimento = data
            item.rrule = regra
            item.status = Lancamento.status_para_vencimento(data)
        self.repository.salvar_serie(futuros)

    def alternar_status(self, lancamento_id: int) -> Lancamento:
        lancamento = self.buscar_por_id(lancamento_id)
        if lancamento.status == StatusLancamento.REALIZADO:
            lancamento.status = Lancamento.status_para_vencimento(lancamento.data_vencimento)
            lancamento.data_pagamento = None
        else:
            lancamento.status = StatusLancamento.REALIZADO
            lancamento.data_pagamento = datetime.now()
        return self.repository.atualizar(lancamento)

    def deletar_lancamento(self, lancamento_id: int, alcance: str = "individual") -> None:
        lancamento = self.buscar_por_id(lancamento_id)
        if alcance == "serie":
            if not lancamento.serie_id:
                raise ValueError("O lançamento não pertence a uma série")
            futuros = self.repository.buscar_futuros_da_serie(lancamento)
            self.repository.salvar_serie(
                [item for item in futuros if item.status != StatusLancamento.REALIZADO],
                excluir=True,
            )
        else:
            self.repository.deletar(lancamento)


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
            serie_id=lancamento.serie_id,
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
