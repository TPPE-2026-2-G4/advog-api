from fastapi import HTTPException

from app.models.lancamento import Lancamento
from app.repositories.lancamento import LancamentoRepository
from app.schemas.lancamento import LancamentoCreate


class LancamentoService:
    def __init__(self, repository: LancamentoRepository):
        self.repository = repository

    def list_lancamentos(self) -> list[Lancamento]:
        return self.repository.get_all()

    def create_lancamento(self, lancamento_data: LancamentoCreate) -> Lancamento:
        if lancamento_data.tipo not in ["Entrada", "Saída"]:
            raise HTTPException(status_code=400, detail="Tipo deve ser 'Entrada' ou 'Saída'")

        return self.repository.create(lancamento_data)
