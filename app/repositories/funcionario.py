from sqlalchemy.orm import Session

from app.models.funcionario import Funcionario

class FuncionarioRepository:
  def __init__(self, db_session: Session):
    self.db = db_session

  def buscar_por_id(self, funcionario_id: int) -> Funcionario | None:
    return self.db.query(Funcionario).filter_by(funcionario_id = funcionario_id).first()
  
  def buscar_por_email(self, email: str) -> Funcionario | None:
    return self.db.query(Funcionario).filter_by(email = email).first()

  def criar(self, funcionario: Funcionario) -> Funcionario:
    self.db.add(funcionario)
    self.db.commit()
    self.db.refresh(funcionario)
    return funcionario

  def atualizar(self, funcionario: Funcionario) -> Funcionario:
    self.db.commit()
    self.db.refresh(funcionario)
    return funcionario