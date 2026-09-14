from fastapi import HTTPException

from app.models.lancamento import Lancamento
from app.repositories.lancamento import LancamentoRepository
from app.schemas.lancamento import (
    LancamentoCreate,
    LancamentoStatusUpdate,
    LancamentoUpdate,
)


class LancamentoService:
    def __init__(self, repository: LancamentoRepository):
        self.repository = repository

    def list_lancamentos(self) -> list[Lancamento]:
        return self.repository.get_all()

    def create_lancamento(self, lancamento_data: LancamentoCreate) -> Lancamento:
        if lancamento_data.tipo not in ["Entrada", "Saída"]:
            raise HTTPException(status_code=400, detail="Tipo deve ser 'Entrada' ou 'Saída'")

        return self.repository.create(lancamento_data)

    def update_lancamento(self, lancamento_id: int, lancamento_data: LancamentoUpdate) -> Lancamento:
        db_lancamento = self.repository.get_by_id(lancamento_id)
        if not db_lancamento:
            raise HTTPException(status_code=404, detail="Lançamento não encontrado")

        if lancamento_data.tipo and lancamento_data.tipo not in ["Entrada", "Saída"]:
            raise HTTPException(status_code=400, detail="Tipo deve ser 'Entrada' ou 'Saída'")

        update_data = lancamento_data.model_dump(exclude_unset=True)
        return self.repository.update(db_lancamento, update_data)

    def update_status(self, lancamento_id: int, status_update: LancamentoStatusUpdate) -> Lancamento:
        db_lancamento = self.repository.get_by_id(lancamento_id)
        if not db_lancamento:
            raise HTTPException(status_code=404, detail="Lançamento não encontrado")

        status = status_update.status
        tipo = db_lancamento.tipo

        valid_statuses = ["Pendente"]
        if tipo == "Saída":
            valid_statuses.append("Pago")
        elif tipo == "Entrada":
            valid_statuses.append("Recebido")

        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Status '{status}' inválido para lançamento do tipo '{tipo}'. Valores permitidos: {', '.join(valid_statuses)}"
            )

        return self.repository.update(db_lancamento, {"status": status})

    def delete_lancamento(self, lancamento_id: int) -> None:
        db_lancamento = self.repository.get_by_id(lancamento_id)
        if not db_lancamento:
            raise HTTPException(status_code=404, detail="Lançamento não encontrado")
            
        self.repository.delete(db_lancamento)
