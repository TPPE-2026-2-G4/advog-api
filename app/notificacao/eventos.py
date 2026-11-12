"""Notificações disparadas por acontecimentos (atribuição, novo cliente, mudança de status).

Quem recebe:
- **Administradores** recebem o aviso de tudo.
- **Usuários comuns** recebem só o que é relacionado a eles (são o responsável pelo processo,
  da atividade ou do cliente).
- Quem fez a ação não é avisado dela.

Falhar ao notificar nunca pode atrapalhar a operação principal: erros são só registrados.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable, Iterable
from functools import wraps

from sqlalchemy.orm import Session, joinedload

from app.core.permissoes import eh_administrador
from app.funcionario.model import Funcionario, StatusFuncionario
from app.notificacao.model import Notificacao, TipoNotificacao
from app.notificacao.repository import NotificacaoRepository

logger = logging.getLogger(__name__)

Mensagem = tuple[TipoNotificacao, str, str]  # (tipo, título, texto)


def formatar_data(data) -> str:
    return data.strftime("%d/%m/%Y") if data else "sem data"


def _seguro(metodo):
    """Registra e engole falhas: a notificação é secundária em relação à ação do usuário."""

    @wraps(metodo)
    def envolvido(self, *args, **kwargs):
        try:
            return metodo(self, *args, **kwargs)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao gerar notificação (%s)", metodo.__name__)
            with contextlib.suppress(Exception):
                self.db.rollback()
            return 0

    return envolvido


def funcionarios_ativos(db: Session) -> list[Funcionario]:
    return (
        db.query(Funcionario)
        .options(joinedload(Funcionario.cargo))
        .filter(Funcionario.status == StatusFuncionario.ATIVO)
        .all()
    )


def destinatarios(
    db: Session, relacionados: Iterable[int | None], ator_id: int | None = None
) -> list[Funcionario]:
    """Administradores + os relacionados ao fato, sem repetir e sem o autor da ação."""
    ids = {i for i in relacionados if i is not None}
    escolhidos = [
        f
        for f in funcionarios_ativos(db)
        if (eh_administrador(f) or f.funcionario_id in ids) and f.funcionario_id != ator_id
    ]
    return escolhidos


class NotificacaoEventos:
    def __init__(self, db: Session):
        self.db = db
        self.repository = NotificacaoRepository(db)

    def _nome(self, funcionario_id: int | None) -> str | None:
        if funcionario_id is None:
            return None
        funcionario = self.db.get(Funcionario, funcionario_id)
        return funcionario.nome if funcionario else None

    def _enviar(
        self,
        relacionados: Iterable[int | None],
        ator_id: int | None,
        link: str,
        montar: Callable[[bool], Mensagem],
    ) -> int:
        """Cria uma notificação por destinatário. `montar(eh_relacionado)` devolve o texto."""
        ids = {i for i in relacionados if i is not None}
        criadas = []
        for destino in destinatarios(self.db, ids, ator_id):
            tipo, titulo, texto = montar(destino.funcionario_id in ids)
            criadas.append(
                Notificacao(
                    funcionario_id=destino.funcionario_id,
                    tipo=tipo,
                    titulo=titulo[:150],
                    mensagem=texto,
                    link_destino=link,
                )
            )
        return self.repository.criar_varias(criadas)

    # ── atividades ──────────────────────────────────────────────────────
    @_seguro
    def atividade_criada(self, atividade, ator_id: int | None = None) -> int:
        responsaveis = [f.funcionario_id for f in atividade.funcionarios]
        nomes = ", ".join(f.nome for f in atividade.funcionarios)
        prazo = formatar_data(atividade.data_prazo)

        def montar(relacionado: bool) -> Mensagem:
            if relacionado:
                return (
                    TipoNotificacao.ATRIBUICAO,
                    "Nova atividade atribuída a você",
                    f'Você é responsável pela atividade "{atividade.titulo}" (prazo: {prazo}).',
                )
            destino = f"atribuída a {nomes}" if nomes else "criada sem responsável"
            return (
                TipoNotificacao.ATRIBUICAO,
                "Nova atividade criada",
                f'A atividade "{atividade.titulo}" foi {destino} (prazo: {prazo}).',
            )

        return self._enviar(responsaveis, ator_id, "/atividades", montar)

    @_seguro
    def atividade_atribuida(self, atividade, novos_ids: Iterable[int], ator_id=None) -> int:
        novos = {i for i in novos_ids}
        if not novos:
            return 0
        nomes = ", ".join(f.nome for f in atividade.funcionarios if f.funcionario_id in novos)
        prazo = formatar_data(atividade.data_prazo)

        def montar(relacionado: bool) -> Mensagem:
            if relacionado:
                return (
                    TipoNotificacao.ATRIBUICAO,
                    "Você foi designado(a) para uma atividade",
                    f'Você agora é responsável pela atividade "{atividade.titulo}" '
                    f"(prazo: {prazo}).",
                )
            return (
                TipoNotificacao.ATRIBUICAO,
                "Atividade atribuída",
                f'A atividade "{atividade.titulo}" foi atribuída a {nomes}.',
            )

        return self._enviar(novos, ator_id, "/atividades", montar)

    # ── processos ───────────────────────────────────────────────────────
    @_seguro
    def processo_atribuido(self, processo, novo: bool = False, ator_id: int | None = None) -> int:
        """Processo criado (`novo=True`) ou com responsável alterado."""
        if processo.funcionario_id is None and not novo:
            return 0
        responsavel = self._nome(processo.funcionario_id)
        quem = f"atribuído a {responsavel}" if responsavel else "cadastrado sem responsável"

        def montar(relacionado: bool) -> Mensagem:
            if relacionado:
                return (
                    TipoNotificacao.ATRIBUICAO,
                    "Processo atribuído a você",
                    f'O processo {processo.cnj} — "{processo.titulo}" foi atribuído a você.',
                )
            return (
                TipoNotificacao.ATRIBUICAO,
                "Novo processo cadastrado" if novo else "Responsável do processo alterado",
                f'O processo {processo.cnj} — "{processo.titulo}" foi {quem}.',
            )

        return self._enviar([processo.funcionario_id], ator_id, "/processos", montar)

    @_seguro
    def processo_status_alterado(self, processo, status_anterior, ator_id=None) -> int:
        antes = getattr(status_anterior, "value", status_anterior)
        depois = getattr(processo.status, "value", processo.status)

        def montar(_relacionado: bool) -> Mensagem:
            return (
                TipoNotificacao.STATUS_PROCESSO,
                "Status do processo alterado",
                f'O processo {processo.cnj} — "{processo.titulo}" passou de '
                f'"{antes}" para "{depois}".',
            )

        return self._enviar([processo.funcionario_id], ator_id, "/processos", montar)

    # ── clientes ────────────────────────────────────────────────────────
    @_seguro
    def cliente_criado(self, cliente, ator_id: int | None = None) -> int:
        link = f"/clientes?clienteId={cliente.cliente_id}"

        def montar(relacionado: bool) -> Mensagem:
            if relacionado:
                return (
                    TipoNotificacao.NOVO_CLIENTE,
                    "Novo cliente sob sua responsabilidade",
                    f"{cliente.nome} foi cadastrado(a) e está sob a sua responsabilidade.",
                )
            return (
                TipoNotificacao.NOVO_CLIENTE,
                "Novo cliente cadastrado",
                f"{cliente.nome} foi cadastrado(a) como novo cliente.",
            )

        return self._enviar([cliente.responsavel_id], ator_id, link, montar)

    @_seguro
    def cliente_atribuido(self, cliente, ator_id: int | None = None) -> int:
        if cliente.responsavel_id is None:
            return 0
        responsavel = self._nome(cliente.responsavel_id)
        link = f"/clientes?clienteId={cliente.cliente_id}"

        def montar(relacionado: bool) -> Mensagem:
            if relacionado:
                return (
                    TipoNotificacao.ATRIBUICAO,
                    "Cliente atribuído a você",
                    f"{cliente.nome} agora está sob a sua responsabilidade.",
                )
            return (
                TipoNotificacao.ATRIBUICAO,
                "Responsável do cliente alterado",
                f"{cliente.nome} foi atribuído(a) a {responsavel}.",
            )

        return self._enviar([cliente.responsavel_id], ator_id, link, montar)
