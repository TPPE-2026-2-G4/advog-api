from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.arquivo.model import Arquivo  # noqa: F401  (destino da FK de arquivo_id)
from app.config.database import Base
from app.processo.model import Processo  # noqa: F401  (destino da FK de processo_id)


class ProcessoArquivo(Base):
    __tablename__ = "processos_arquivos"

    processo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("processos.processo_id", ondelete="CASCADE"), primary_key=True
    )
    arquivo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arquivos.arquivo_id", ondelete="CASCADE"), primary_key=True
    )
