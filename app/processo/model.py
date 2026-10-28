import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.funcionario.model import Funcionario


class StatusProcesso(enum.StrEnum):
    EM_ANALISE = "Em Análise"
    ATIVO = "Ativo"
    CONCLUIDO = "Concluído"
    ARQUIVADO = "Arquivado"


class Processo(Base):
    __tablename__ = "processos"

    processo_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    cnj: Mapped[str] = mapped_column(String(25), unique=True, index=True, nullable=False)
    titulo: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[StatusProcesso] = mapped_column(
        Enum(
            StatusProcesso,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        default=StatusProcesso.EM_ANALISE,
    )
    tribunal: Mapped[str] = mapped_column(String(100), nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False)
    data_inicio: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data_realizado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data_prazo: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.cliente_id"), nullable=False
    )
    funcionario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("funcionarios.funcionario_id"), nullable=True
    )

    documentos: Mapped[list["DocumentoProcesso"]] = relationship(
        "DocumentoProcesso", back_populates="processo", cascade="all, delete-orphan"
    )


class DocumentoProcesso(Base):
    __tablename__ = "documentos_processo"

    documento_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    processo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("processos.processo_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    chave_minio: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    origem: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    entrada_tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    data_upload: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    funcionario_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("funcionarios.funcionario_id", ondelete="SET NULL"),
        nullable=True,
    )

    processo: Mapped["Processo"] = relationship("Processo", back_populates="documentos")
    funcionario: Mapped["Funcionario | None"] = relationship("Funcionario")
