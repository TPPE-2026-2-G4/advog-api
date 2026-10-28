from sqlalchemy.orm import Session

from app.atividade.model import Atividade
from app.funcionario.model import Funcionario


class AtividadeFuncionarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_atividade(self, atividade_id: int) -> Atividade | None:
        return self.db.get(Atividade, atividade_id)

    def buscar_funcionario(self, funcionario_id: int) -> Funcionario | None:
        return self.db.get(Funcionario, funcionario_id)

    def trocar_responsavel(
        self, atividade: Atividade, atual: Funcionario, novo: Funcionario
    ) -> Atividade:
        atividade.funcionarios.remove(atual)
        atividade.funcionarios.append(novo)
        self.db.commit()
        self.db.refresh(atividade)
        return atividade
