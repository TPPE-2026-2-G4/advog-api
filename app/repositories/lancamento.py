from sqlalchemy.orm import Session

from app.models.lancamento import Lancamento
from app.schemas.lancamento import LancamentoCreate


class LancamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Lancamento]:
        return self.db.query(Lancamento).all()

    def create(self, lancamento_data: LancamentoCreate) -> Lancamento:
        db_lancamento = Lancamento(**lancamento_data.model_dump())
        self.db.add(db_lancamento)
        self.db.commit()
        self.db.refresh(db_lancamento)
        return db_lancamento

    def get_by_id(self, lancamento_id: int) -> Lancamento | None:
        return self.db.query(Lancamento).filter(Lancamento.lancamento_id == lancamento_id).first()

    def update(self, db_lancamento: Lancamento, update_data: dict) -> Lancamento:
        for key, value in update_data.items():
            setattr(db_lancamento, key, value)
        self.db.commit()
        self.db.refresh(db_lancamento)
        return db_lancamento

    def delete(self, db_lancamento: Lancamento) -> None:
        self.db.delete(db_lancamento)
        self.db.commit()
