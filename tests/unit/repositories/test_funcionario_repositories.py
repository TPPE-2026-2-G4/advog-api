import pytest
from app.repositories.funcionario import FuncionarioRepository
from app.models.funcionario import Funcionario, StatusFuncionario

@pytest.mark.parametrize("nome,email", [
  ("Ana Beatriz Souza", "ana.souza@test.com"),
  ("Carlos Eduardo Lima", "carlos.lima@test.com"),
  ("Patrícia Almeida", "patricia.almeida@test.com"),
  ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
  ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
])
def test_criar_funcionario(db_session, nome, email):
    repository = FuncionarioRepository(db_session)
    funcionario = Funcionario(
      nome=nome,
      email=email,
    )

    criacao = repository.criar(funcionario)

    assert criacao.funcionario_id is not None
    assert criacao.nome == nome
    assert criacao.email == email
    assert criacao.senha_hash is None
    assert criacao.uf_oab is None
    assert criacao.numero_oab is None
    assert criacao.status == StatusFuncionario.PENDENTE
    assert criacao.exibicaoInstitucional is False

def test_obter_todos_funcionarios(db_session):
  repository = FuncionarioRepository(db_session)
  funcionario1 = Funcionario(
    nome="Ana Beatriz Souza",
    email="ana.souza@test.com",
  )
  funcionario2 = Funcionario(
    nome="Outro Usuário",
    email="outro.usuario@test.com",
  )

  repository.criar(funcionario1)
  repository.criar(funcionario2)

  todos = repository.buscar_todos()

  assert len(todos) == 2
  assert todos[0].nome == "Ana Beatriz Souza"
  assert todos[0].email == "ana.souza@test.com"
  assert todos[1].nome == "Outro Usuário"
  assert todos[1].email == "outro.usuario@test.com"

def test_buscar_por_id(db_session):
  repository = FuncionarioRepository(db_session)
  funcionario1 = Funcionario(
    nome="Ana Beatriz Souza",
    email="ana.souza@test.com",
  )
  funcionario2 = Funcionario(
    nome="Outro Usuário",
    email="outro.usuario@test.com",
  )

  criacao1 = repository.criar(funcionario1)
  criacao2 = repository.criar(funcionario2)
  encontrado1 = repository.buscar_por_id(criacao1.funcionario_id)
  encontrado2 = repository.buscar_por_id(criacao2.funcionario_id)

  assert encontrado1 is not None
  assert encontrado1.nome == "Ana Beatriz Souza"
  assert encontrado1.email == "ana.souza@test.com"
  assert encontrado2 is not None
  assert encontrado2.nome == "Outro Usuário"
  assert encontrado2.email == "outro.usuario@test.com"

def test_buscar_por_email(db_session):
  repository = FuncionarioRepository(db_session)
  funcionario = Funcionario(
    nome="Ana Beatriz Souza",
    email="ana.souza@test.com"
  )

  criacao = repository.criar(funcionario)
  encontrado = repository.buscar_por_email(criacao.email)

  assert encontrado is not None
  assert encontrado.nome == "Ana Beatriz Souza"
  assert encontrado.email == "ana.souza@test.com"

def test_atualizar_funcionario(db_session):
  repository = FuncionarioRepository(db_session)
  funcionario = Funcionario(
    nome="Ana Beatriz Souza",
    email="ana.souza@test.com"
  )

  criacao = repository.criar(funcionario)

  criacao.nome = "Ana Beatriz Souza Updated"
  criacao.email = "ana.souza_updated@test.com"

  atualizacao = repository.atualizar(criacao)

  assert atualizacao is not None
  assert atualizacao.nome == "Ana Beatriz Souza Updated"
  assert atualizacao.email == "ana.souza_updated@test.com"

def test_apagar_funcionario(db_session):
  repository = FuncionarioRepository(db_session)
  funcionario1 = Funcionario(
    nome="Ana Beatriz Souza",
    email="ana.souza@test.com",
  )
  funcionario2 = Funcionario(
    nome="Outro Usuário",
    email="outro.usuario@test.com",
  )

  funcionarioADeletar =repository.criar(funcionario1)
  repository.criar(funcionario2)
  busca = repository.buscar_todos()

  assert len(busca) == 2
  assert busca[0].nome == "Ana Beatriz Souza"
  assert busca[1].nome == "Outro Usuário"

  repository.deletar(funcionarioADeletar)

  assert repository.buscar_por_id(busca[0].funcionario_id) is None
  assert repository.buscar_por_id(busca[1].funcionario_id) is not None
  assert len(repository.buscar_todos()) == 1
  assert repository.buscar_todos()[0].nome == "Outro Usuário"