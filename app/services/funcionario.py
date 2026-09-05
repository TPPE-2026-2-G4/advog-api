from sqlalchemy.orm import Session

from app.repositories.funcionario import FuncionarioRepository
from app.models.funcionario import Funcionario, StatusFuncionario
from app.schemas.funcionario import FuncionarioCreate, FuncionarioPrimeiroAcesso
from app.utils.seguranca import hash_senha

class FuncionarioService:
  def __init__(self, db_session: Session):
    self.repository = FuncionarioRepository(db_session)

  def buscar_todos(self) -> list[Funcionario]:
    return self.repository.buscar_todos()
    
  def criar_funcionario(self, dados: FuncionarioCreate) -> Funcionario:
    if self.repository.buscar_por_email(dados.email):
      raise ValueError("Email já cadastrado")
    
    req = Funcionario(
      nome=dados.nome,
      email=dados.email
    )
    return self.repository.criar(req)

  def primeiro_acesso(self, funcionario_id: int, dados: FuncionarioPrimeiroAcesso) -> Funcionario:
    funcionario = self.repository.buscar_por_id(funcionario_id)
    if not funcionario:
      raise ValueError("Funcionário não encontrado")
    if funcionario and funcionario.status != StatusFuncionario.PENDENTE:
      raise ValueError("Funcionário já teve a conta ativada")

    dados_enviados = dados.model_dump(exclude_unset=True)

    if "nome" in dados_enviados:
      funcionario.nome = dados.nome 
    if "senha" in dados_enviados:
      funcionario.senha_hash = hash_senha(dados.senha)
    if "uf_oab" in dados_enviados:
      funcionario.uf_oab = dados.uf_oab
    if "numero_oab" in dados_enviados:  
      funcionario.numero_oab = dados.numero_oab

    funcionario.status = StatusFuncionario.ATIVO
    
    return self.repository.atualizar(funcionario)

  def revogar_acesso(self, funcionario_id: int) -> Funcionario:
    funcionario = self.repository.buscar_por_id(funcionario_id)
    if not funcionario:
      raise ValueError("Funcionário não encontrado")
    if funcionario and funcionario.status != StatusFuncionario.ATIVO:
      raise ValueError("Funcionário não está ativo")

    funcionario.status = StatusFuncionario.INATIVO
    return self.repository.atualizar(funcionario)