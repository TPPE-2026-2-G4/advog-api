import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base
from app.funcionario.model import Funcionario  # noqa: F401  (destino da FK de funcionario_id)
from app.processo.model import Processo  # noqa: F401  (destino da FK de processo_id)


class TipoMovimentacaoProcesso(enum.StrEnum):
    CRIACAO_PROCESSO = "CRIACAO_PROCESSO"
    ATUALIZACAO_PROCESSO = "ATUALIZACAO_PROCESSO"
    SINCRONIZACAO_TRIBUNAL = "SINCRONIZACAO_TRIBUNAL"
    UPLOAD_ARQUIVO = "UPLOAD_ARQUIVO"
    EXCLUSAO_ARQUIVO = "EXCLUSAO_ARQUIVO"
    CRIACAO_ATIVIDADE = "CRIACAO_ATIVIDADE"
    ATUALIZACAO_ETAPA_ATIVIDADE = "ATUALIZACAO_ETAPA_ATIVIDADE"
    EXCLUSAO_ATIVIDADE = "EXCLUSAO_ATIVIDADE"


class ProcessoMovimentacao(Base):
    __tablename__ = "processos_movimentacoes"

    movimentacao_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    processo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("processos.processo_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    funcionario_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("funcionarios.funcionario_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tipo_movimentacao: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    data_movimentacao: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
