import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class TipoNotificacao(StrEnum):
    ATRIBUICAO = "ATRIBUICAO"
    VENCIMENTO_7D = "VENCIMENTO_7D"
    VENCIMENTO_1D = "VENCIMENTO_1D"
    VENCIMENTO_HOJE = "VENCIMENTO_HOJE"
    ATRASO = "ATRASO"
    NOVO_CLIENTE = "NOVO_CLIENTE"
    STATUS_PROCESSO = "STATUS_PROCESSO"
    SISTEMA = "SISTEMA"


class Notificacao(Base):
    __tablename__ = "notificacoes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    funcionario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("funcionarios.funcionario_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[TipoNotificacao] = mapped_column(
        SQLEnum(TipoNotificacao, name="tipo_notificacao_enum"),
        default=TipoNotificacao.SISTEMA,
        nullable=False,
        index=True,
    )
    lida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    link_destino: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
