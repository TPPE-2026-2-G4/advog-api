import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.notificacao.model import TipoNotificacao


class NotificacaoBase(BaseModel):
    titulo: str = Field(
        ...,
        max_length=150,
        description="Título objetivo da notificação",
    )
    mensagem: str = Field(
        ...,
        description="Conteúdo detalhado da notificação",
    )
    tipo: TipoNotificacao = Field(
        default=TipoNotificacao.SISTEMA,
        description="Categoria/evento que originou a notificação",
    )
    link_destino: str | None = Field(
        default=None,
        max_length=255,
        description="Rota no frontend para redirecionamento ao clicar (ex: /processos/uuid)",
    )


class NotificacaoCreate(NotificacaoBase):
    funcionario_id: int = Field(
        ...,
        description="ID do funcionário destinatário da notificação",
    )


class NotificacaoRead(NotificacaoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    funcionario_id: int
    lida: bool
    criado_em: datetime


class NotificacaoPaginatedResponse(BaseModel):
    items: list[NotificacaoRead]
    total: int
    nao_lidas_count: int
    page: int
    size: int


class ContagemNaoLidasResponse(BaseModel):
    total_nao_lidas: int
