from typing import List
from fastapi import HTTPException
from app.schemas.lancamento import LancamentoCreate
from app.repositories.lancamento import LancamentoRepository
from app.models.lancamento import Lancamento

class LancamentoService:
    def __init__(self, repository: LancamentoRepository):
        self.repository = repository

    def list_lancamentos(self) -> List[Lancamento]:
        return self.repository.get_all()

    def create_lancamento(self, lancamento_data: LancamentoCreate) -> Lancamento:
        if lancamento_data.tipo not in ["Entrada", "Saída"]:
            raise HTTPException(status_code=400, detail="Tipo deve ser 'Entrada' ou 'Saída'")
        
        return self.repository.create(lancamento_data)
