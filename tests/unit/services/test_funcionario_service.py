import pytest
from unittest.mock import MagicMock
from app.services.funcionario import FuncionarioService
from app.schemas.funcionario import FuncionarioCreate, FuncionarioPrimeiroAcesso
from app.models.funcionario import Funcionario, StatusFuncionario
from app.repositories.funcionario import FuncionarioRepository

def test_criar_funcionario_com_email_duplicado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_email.return_value = Funcionario(
      nome="Outro Usuário",
      email="ana.souza@test.com",
    )

    with pytest.raises(ValueError, match="Email já cadastrado"):
        service.criar_funcionario(FuncionarioCreate(nome="Ana Beatriz Souza", email="ana.souza@test.com"))

@pytest.mark.parametrize("nome,email", [
  ("Ana Beatriz Souza", "ana.souza@test.com"),
  ("Carlos Eduardo Lima", "carlos.lima@test.com"),
  ("Patrícia Almeida", "patricia.almeida@test.com"),
  ("José da Conceição Neto Sobrinho de Almeida Júnior", "jose.longo@test.com"),
  ("Rafael Nascimento", "RAFAEL.NASCIMENTO@TEST.COM"),
])
def test_criar_funcionario_com_email_unico(nome, email):
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_email.return_value = None
    service.repository.criar.return_value = Funcionario(
      nome=nome,
      email=email.lower(),
      funcionario_id = 1,
      status = StatusFuncionario.PENDENTE,
      uf_oab = None,
      numero_oab = None,
      exibicaoInstitucional = False,
    )

    funcionario = service.criar_funcionario(FuncionarioCreate(nome=nome, email=email))

    assert isinstance(funcionario, Funcionario)
    assert funcionario is not None
    assert funcionario.nome == nome
    assert funcionario.email == email.lower()
    assert funcionario.status == StatusFuncionario.PENDENTE

def test_buscar_todos_retorna_lista_de_funcionarios():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_todos.return_value = [
        Funcionario(
            nome="Ana Beatriz Souza",
            email="ana.souza@test.com",
            funcionario_id = 1,
            status = StatusFuncionario.PENDENTE,
            uf_oab = None,
            numero_oab = None,
            exibicaoInstitucional = False,
        ),
        Funcionario(
            nome="Outro Usuário",
            email="outro.usuario@test.com",
            funcionario_id = 2,
            status = StatusFuncionario.PENDENTE,
            uf_oab = None,
            numero_oab = None,
            exibicaoInstitucional = False,
        ),
    ]

    funcionarios = service.buscar_todos()

    assert isinstance(funcionarios, list)
    assert len(funcionarios) == 2
    assert funcionarios[0].nome == "Ana Beatriz Souza"
    assert funcionarios[0].email == "ana.souza@test.com"
    assert funcionarios[1].nome == "Outro Usuário"
    assert funcionarios[1].email == "outro.usuario@test.com"
    assert isinstance(funcionarios[0], Funcionario)
    assert isinstance(funcionarios[1], Funcionario)

def test_primeiro_acesso_funcionario_nao_encontrado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.primeiro_acesso(1, FuncionarioPrimeiroAcesso(senha="test123"))

def test_primeiro_acesso_funcionario_com_conta_pendente_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicaoInstitucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario

    with pytest.raises(ValueError, match="Funcionário já teve a conta ativada"):
        service.primeiro_acesso(1, FuncionarioPrimeiroAcesso(senha="test123"))

def test_primeiro_acesso_funcionario_com_sucesso():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Ana Beatriz Souza",
        email="ana.souza@test.com",
        funcionario_id=1,
        status=StatusFuncionario.PENDENTE,
        uf_oab=None,
        numero_oab=None,
        exibicaoInstitucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario
    service.repository.atualizar.return_value = funcionario

    dados_acesso = FuncionarioPrimeiroAcesso(senha="test123", nome="Ana Beatriz Souza", uf_oab="SP", numero_oab="12345")
    funcionario_atualizado = service.primeiro_acesso(1, dados_acesso)

    assert isinstance(funcionario_atualizado, Funcionario)
    assert funcionario_atualizado.nome == "Ana Beatriz Souza"
    assert funcionario_atualizado.email == "ana.souza@test.com"
    assert funcionario_atualizado.uf_oab == "SP"
    assert funcionario_atualizado.numero_oab == "12345"
    assert funcionario_atualizado.status == StatusFuncionario.ATIVO
  
def test_mudar_acesso_funcionario_nao_encontrado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.mudar_acesso(1)

def test_mudar_acesso_funcionario_com_conta_pendente_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        status=StatusFuncionario.PENDENTE,
        uf_oab=None,
        numero_oab=None,
        exibicaoInstitucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario

    with pytest.raises(ValueError, match="Funcionário ainda não ativou a conta"):
        service.mudar_acesso(1)

def test_mudar_acesso_funcionario_com_conta_ativa_para_inativa():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicaoInstitucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario

    funcionario_sem_acesso = Funcionario(
          nome="Usuário Teste",
          email="usuario.teste@test.com",
          funcionario_id=1,
          status=StatusFuncionario.INATIVO,
          uf_oab=None,
          numero_oab=None,
          exibicaoInstitucional=False,
    )

    service.repository.atualizar.return_value = funcionario

    funcionario_atualizado = service.mudar_acesso(1)

    assert isinstance(funcionario_atualizado, Funcionario)
    assert funcionario_atualizado.status == StatusFuncionario.INATIVO

def test_mudar_acesso_funcionario_com_conta_inativa_para_ativa():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        status=StatusFuncionario.INATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicaoInstitucional=False,
    )

    service.repository.buscar_por_id.return_value = funcionario

    funcionario_sem_acesso = Funcionario(
          nome="Usuário Teste",
          email="usuario.teste@test.com",
          funcionario_id=1,
          status=StatusFuncionario.ATIVO,
          uf_oab=None,
          numero_oab=None,
          exibicaoInstitucional=False,
    )

    service.repository.atualizar.return_value = funcionario

    funcionario_atualizado = service.mudar_acesso(1)

    assert isinstance(funcionario_atualizado, Funcionario)
    assert funcionario_atualizado.status == StatusFuncionario.ATIVO

def test_apagar_funcionario_nao_encontrado_gera_erro():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.apagar_funcionario(1)

def test_apagar_funcionario_retorna_funcionario_apagado():
    service = FuncionarioService.__new__(FuncionarioService)
    service.repository = MagicMock(spec=FuncionarioRepository)
    funcionario = Funcionario(
        nome="Usuário Teste",
        email="usuario.teste@test.com",
        funcionario_id=1,
        status=StatusFuncionario.ATIVO,
        uf_oab=None,
        numero_oab=None,
        exibicaoInstitucional=False,
    )
    service.repository.buscar_por_id.return_value = funcionario
    service.repository.deletar.return_value = funcionario

    funcionario = service.apagar_funcionario(1)

    assert isinstance(funcionario, Funcionario)
    assert funcionario.funcionario_id == 1

def test_construtor_cria_repository_com_a_sessao_informada(db_session):
    service = FuncionarioService(db_session)

    assert isinstance(service.repository, FuncionarioRepository)
    assert service.repository.db is db_session