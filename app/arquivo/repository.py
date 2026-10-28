from sqlalchemy.orm import Session

from app.arquivo.model import Arquivo

LINK_ARQUIVO_PADRAO = ""


class ArquivoRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_id(self, arquivo_id: int) -> Arquivo | None:
        return self.db.get(Arquivo, arquivo_id)

    def adicionar(self, arquivo: Arquivo) -> Arquivo:
        self.db.add(arquivo)
        self.db.commit()
        self.db.refresh(arquivo)
        return arquivo

    def deletar(self, arquivo: Arquivo) -> None:
        self.db.delete(arquivo)
        self.db.commit()

    def obter_padrao(self) -> Arquivo:
        arquivo = self.db.query(Arquivo).filter(Arquivo.bucket_link == LINK_ARQUIVO_PADRAO).first()
        if arquivo is None:
            arquivo = Arquivo(
                nome_arquivo="sem-arquivo",
                tipo_mime="application/octet-stream",
                tamanho_bytes=0,
                bucket_link=LINK_ARQUIVO_PADRAO,
                origem="sistema",
            )
            self.db.add(arquivo)
            self.db.flush()
        return arquivo
