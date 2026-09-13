from sqlalchemy.orm import Session
from typing import List
from app.models.lancamento import Lancamento
from app.schemas.lancamento import LancamentoCreate

class LancamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Lancamento]:
        return self.db.query(Lancamento).all()

    def create(self, lancamento_data: LancamentoCreate) -> Lancamento:
        db_lancamento = Lancamento(
            tipo=lancamento_data.tipo,
            titulo=lancamento_data.titulo,
            descricao=lancamento_data.descricao,
            valor=lancamento_data.valor,
            data=lancamento_data.data,
            categoria=lancamento_data.categoria,
            status=lancamento_data.status,
            recorrente=lancamento_data.recorrente
        )
        self.db.add(db_lancamento)
        self.db.commit()
        self.db.refresh(db_lancamento)
        return db_lancamento
