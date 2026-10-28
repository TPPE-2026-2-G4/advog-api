from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.arquivo.model import Arquivo  # noqa: F401  (destino da FK de arquivo_id)
from app.cliente.model import Cliente  # noqa: F401  (destino da FK de cliente_id)
from app.config.database import Base


class ClienteArquivo(Base):
    __tablename__ = "clientes_arquivos"

    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.cliente_id", ondelete="CASCADE"), primary_key=True
    )
    arquivo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arquivos.arquivo_id", ondelete="CASCADE"), primary_key=True
    )
