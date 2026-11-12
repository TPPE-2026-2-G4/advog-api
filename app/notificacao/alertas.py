"""Alertas automáticos de prazos e de processos críticos (job periódico).

Os avisos seguem a configuração do escritório, definida na tela Ajustes:

- `dias_prazo_proximo`: com quantos dias de antecedência começa o aviso dos prazos;
- `dias_processo_critico`: após quantos dias sem movimentação um processo vira "crítico".

Quem recebe: administradores veem tudo (processos, atividades e lançamentos); usuários comuns
só o que é deles (processos e atividades pelos quais são responsáveis). Os lançamentos
financeiros, que não têm responsável, vão também para quem pode visualizar o financeiro.

O job pode rodar quantas vezes quiser: a `chave` de cada alerta impede avisar duas vezes a mesma
pessoa pelo mesmo motivo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.atividade.model import Atividade
from app.core.permissoes import eh_administrador, pode_visualizar_financeiro
from app.institucional.model import Institucional
from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento
from app.notificacao.eventos import formatar_data, funcionarios_ativos
from app.notificacao.model import Notificacao, TipoNotificacao
from app.notificacao.repository import NotificacaoRepository
from app.processo.model import Processo, StatusProcesso

logger = logging.getLogger(__name__)

STATUS_FINALIZADOS = (StatusProcesso.CONCLUIDO, StatusProcesso.ARQUIVADO)
PADRAO_DIAS = 15


@dataclass(frozen=True)
class Alerta:
    funcionario_id: int
    chave: str
    tipo: TipoNotificacao
    titulo: str
    mensagem: str
    link: str


def fase_do_prazo(dias_restantes: int, antecedencia: int) -> TipoNotificacao | None:
    """Em que fase do prazo estamos hoje (e se vale avisar)."""
    if dias_restantes < 0:
        return TipoNotificacao.ATRASO
    if dias_restantes == 0:
        return TipoNotificacao.VENCIMENTO_HOJE
    if dias_restantes == 1:
        return TipoNotificacao.VENCIMENTO_1D
    if dias_restantes <= antecedencia:
        # Primeiro aviso, quando o prazo entra na janela configurada pela pessoa.
        return TipoNotificacao.VENCIMENTO_7D
    return None


def _quando(dias_restantes: int) -> str:
    if dias_restantes < 0:
        dias = abs(dias_restantes)
        return f"está atrasado há {dias} dia{'s' if dias != 1 else ''}"
    if dias_restantes == 0:
        return "vence hoje"
    if dias_restantes == 1:
        return "vence amanhã"
    return f"vence em {dias_restantes} dias"


_TITULO_FASE = {
    TipoNotificacao.ATRASO: "em atraso",
    TipoNotificacao.VENCIMENTO_HOJE: "vence hoje",
    TipoNotificacao.VENCIMENTO_1D: "vence amanhã",
    TipoNotificacao.VENCIMENTO_7D: "prazo se aproxima",
}


class AlertasService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = NotificacaoRepository(db)

    # ── prazos ───────────────────────────────────────────────────────────
    def _alerta_prazo(
        self,
        *,
        funcionario_id: int,
        antecedencia: int,
        hoje: date,
        prazo: datetime,
        entidade: str,
        entidade_id: int,
        rotulo: str,
        nome: str,
        link: str,
    ) -> Alerta | None:
        dias = (prazo.date() - hoje).days
        fase = fase_do_prazo(dias, antecedencia)
        if fase is None:
            return None
        return Alerta(
            funcionario_id=funcionario_id,
            chave=f"prazo:{entidade}:{entidade_id}:{prazo.date().isoformat()}:{fase.value}",
            tipo=fase,
            titulo=f"{rotulo}: {_TITULO_FASE[fase]}",
            mensagem=f"{nome} {_quando(dias)} (prazo: {formatar_data(prazo)}).",
            link=link,
        )

    def gerar_alertas(self, hoje: date | None = None) -> int:
        """Cria os alertas que ainda não existem e devolve quantos foram criados."""
        hoje = hoje or date.today()
        agora = datetime.combine(hoje, datetime.min.time())

        processos = self.db.query(Processo).filter(Processo.status.notin_(STATUS_FINALIZADOS)).all()
        atividades = (
            self.db.query(Atividade)
            .options(joinedload(Atividade.etapa), joinedload(Atividade.funcionarios))
            .filter(Atividade.data_realizado.is_(None))
            .all()
        )
        atividades = [a for a in atividades if (a.etapa.nome or "").strip().lower() != "finalizado"]
        lancamentos = (
            self.db.query(Lancamento)
            .filter(Lancamento.status != StatusLancamento.REALIZADO)
            .filter(Lancamento.data_pagamento.is_(None))
            .all()
        )

        configuracao = self.db.get(Institucional, 1)
        antecedencia = (configuracao.dias_prazo_proximo if configuracao else None) or PADRAO_DIAS
        dias_critico = (configuracao.dias_processo_critico if configuracao else None) or PADRAO_DIAS

        alertas: list[Alerta] = []
        for funcionario in funcionarios_ativos(self.db):
            fid = funcionario.funcionario_id
            admin = eh_administrador(funcionario)

            for processo in processos:
                if not (admin or processo.funcionario_id == fid):
                    continue
                nome = f'O processo {processo.cnj} — "{processo.titulo}"'
                alerta = self._alerta_prazo(
                    funcionario_id=fid,
                    antecedencia=antecedencia,
                    hoje=hoje,
                    prazo=processo.data_prazo,
                    entidade="processo",
                    entidade_id=processo.processo_id,
                    rotulo="Processo",
                    nome=nome,
                    link="/processos",
                )
                if alerta:
                    alertas.append(alerta)

                ultima = processo.data_realizado or processo.data_inicio
                if ultima is not None and ultima < agora - timedelta(days=dias_critico):
                    parado = (hoje - ultima.date()).days
                    alertas.append(
                        Alerta(
                            funcionario_id=fid,
                            chave=(
                                f"critico:{processo.processo_id}:{ultima.date().isoformat()}"
                                f":{dias_critico}"
                            ),
                            tipo=TipoNotificacao.SISTEMA,
                            titulo="Processo crítico",
                            mensagem=(
                                f"{nome} está há {parado} dias sem movimentação "
                                f"(limite configurado: {dias_critico} dias)."
                            ),
                            link="/processos",
                        )
                    )

            for atividade in atividades:
                if not (admin or fid in {f.funcionario_id for f in atividade.funcionarios}):
                    continue
                alerta = self._alerta_prazo(
                    funcionario_id=fid,
                    antecedencia=antecedencia,
                    hoje=hoje,
                    prazo=atividade.data_prazo,
                    entidade="atividade",
                    entidade_id=atividade.atividade_id,
                    rotulo="Atividade",
                    nome=f'A atividade "{atividade.titulo}"',
                    link="/atividades",
                )
                if alerta:
                    alertas.append(alerta)

            if pode_visualizar_financeiro(funcionario):  # lançamentos não têm responsável
                for lancamento in lancamentos:
                    tipo = "A receber" if lancamento.tipo == TipoLancamento.ENTRADA else "A pagar"
                    alerta = self._alerta_prazo(
                        funcionario_id=fid,
                        antecedencia=antecedencia,
                        hoje=hoje,
                        prazo=lancamento.data_vencimento,
                        entidade="lancamento",
                        entidade_id=lancamento.lancamento_id,
                        rotulo=f"Lançamento ({tipo.lower()})",
                        nome=f'O lançamento "{lancamento.titulo}"',
                        link="/calendario",
                    )
                    if alerta:
                        alertas.append(alerta)

        return self._gravar(alertas)

    def _gravar(self, alertas: list[Alerta]) -> int:
        if not alertas:
            return 0
        ja_enviados = self.repository.chaves_existentes(
            {a.funcionario_id for a in alertas}, {a.chave for a in alertas}
        )
        novas = [
            Notificacao(
                funcionario_id=a.funcionario_id,
                chave=a.chave,
                tipo=a.tipo,
                titulo=a.titulo[:150],
                mensagem=a.mensagem,
                link_destino=a.link,
            )
            for a in alertas
            if (a.funcionario_id, a.chave) not in ja_enviados
        ]
        criadas = self.repository.criar_varias(novas)
        logger.info("[JOB ALERTAS] %s notificação(ões) criada(s).", criadas)
        return criadas


def executar_alertas() -> int:
    """Ponto de entrada do job agendado (abre e fecha a própria sessão)."""
    from app.config import database

    db = database.SessionLocal()
    try:
        return AlertasService(db).gerar_alertas()
    except Exception:
        db.rollback()
        logger.exception("[JOB ALERTAS] Falha ao gerar alertas.")
        raise
    finally:
        db.close()
