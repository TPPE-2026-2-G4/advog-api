from sqlalchemy.orm import Session

from app.produtividade.repository import ProdutividadeRepository


class ProdutividadeService:
    def __init__(self, db_session: Session):
        self.repository = ProdutividadeRepository(db_session)
