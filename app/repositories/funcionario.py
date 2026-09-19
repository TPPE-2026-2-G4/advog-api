from sqlalchemy.orm import Session

from app.models.funcionario import Funcionario, StatusFuncionario


class FuncionarioRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def buscar_todos(self) -> list[Funcionario]:
        return self.db.query(Funcionario).all()

    def buscar_visiveis_institucional(self) -> list[Funcionario]:
        return (
            self.db.query(Funcionario)
            .filter(
                Funcionario.status == StatusFuncionario.ATIVO,
                Funcionario.exibicao_institucional.is_(True),
            )
            .all()
        )

    def buscar_por_id(self, funcionario_id: int) -> Funcionario | None:
        return self.db.get(Funcionario, funcionario_id)

    def buscar_por_email(self, email: str) -> Funcionario | None:
        return self.db.query(Funcionario).filter_by(email=email).first()

    def criar(self, funcionario: Funcionario) -> Funcionario:
        self.db.add(funcionario)
        self.db.commit()
        self.db.refresh(funcionario)
        return funcionario

    def atualizar(self, funcionario: Funcionario) -> Funcionario:
        self.db.commit()
        self.db.refresh(funcionario)
        return funcionario

    def deletar(self, funcionario: Funcionario) -> None:
        self.db.delete(funcionario)
        self.db.commit()
