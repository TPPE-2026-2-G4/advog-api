from sqlalchemy.orm import Session

from app.models.funcionario import Funcionario, StatusFuncionario
from app.repositories.cargo import CargoRepository
from app.repositories.funcionario import FuncionarioRepository
from app.schemas.funcionario import FuncionarioCreate, FuncionarioPrimeiroAcesso, FuncionarioUpdate
from app.utils.seguranca import hash_senha


class FuncionarioService:
    def __init__(self, db_session: Session):
        self.repository = FuncionarioRepository(db_session)
        self.cargo_repository = CargoRepository(db_session)

    def buscar_todos(self) -> list[Funcionario]:
        return self.repository.buscar_todos()

    def buscar_visiveis_institucional(self) -> list[Funcionario]:
        return self.repository.buscar_visiveis_institucional()

    def criar_funcionario(self, dados: FuncionarioCreate) -> Funcionario:
        if self.repository.buscar_por_email(dados.email.lower()):
            raise ValueError("Email já cadastrado")

        cargo = self.cargo_repository.buscar_por_id(dados.cargo_id)
        if not cargo:
            raise ValueError("Cargo não encontrado")

        req = Funcionario(nome=dados.nome, email=dados.email.lower(), cargo_id=dados.cargo_id)
        return self.repository.criar(req)

    def primeiro_acesso(self, funcionario_id: int, dados: FuncionarioPrimeiroAcesso) -> Funcionario:
        funcionario = self.repository.buscar_por_id(funcionario_id)
        if not funcionario:
            raise ValueError("Funcionário não encontrado")
        if funcionario.status != StatusFuncionario.PENDENTE:
            raise ValueError("Funcionário já teve a conta ativada")

        dados_enviados = dados.model_dump(exclude_unset=True)

        if dados.nome is not None:
            funcionario.nome = dados.nome
        if dados.senha is not None:
            funcionario.senha_hash = hash_senha(dados.senha)
        if "uf_oab" in dados_enviados:
            funcionario.uf_oab = dados.uf_oab
        if "numero_oab" in dados_enviados:
            funcionario.numero_oab = dados.numero_oab

        funcionario.status = StatusFuncionario.ATIVO

        return self.repository.atualizar(funcionario)

    def mudar_cargo(self, funcionario_id: int, cargo_id: int) -> Funcionario:
        funcionario = self.repository.buscar_por_id(funcionario_id)
        if not funcionario:
            raise ValueError("Funcionário não encontrado")

        cargo = self.cargo_repository.buscar_por_id(cargo_id)
        if not cargo:
            raise ValueError("Cargo não encontrado")

        funcionario.cargo_id = cargo_id
        return self.repository.atualizar(funcionario)

    def mudar_exibicao_institucional(self, funcionario_id: int, exibicao: bool) -> Funcionario:
        funcionario = self.repository.buscar_por_id(funcionario_id)
        if not funcionario:
            raise ValueError("Funcionário não encontrado")

        funcionario.exibicao_institucional = exibicao
        return self.repository.atualizar(funcionario)

    def editar_dados(self, funcionario_id: int, dados: FuncionarioUpdate) -> Funcionario:
        funcionario = self.repository.buscar_por_id(funcionario_id)
        if not funcionario:
            raise ValueError("Funcionário não encontrado")

        dados_enviados = dados.model_dump(exclude_unset=True)

        if dados.nome is not None:
            funcionario.nome = dados.nome
        if dados.senha is not None:
            funcionario.senha_hash = hash_senha(dados.senha)
        if "uf_oab" in dados_enviados:
            funcionario.uf_oab = dados.uf_oab
        if "numero_oab" in dados_enviados:
            funcionario.numero_oab = dados.numero_oab

        return self.repository.atualizar(funcionario)

    def mudar_acesso(self, funcionario_id: int) -> Funcionario:
        funcionario = self.repository.buscar_por_id(funcionario_id)
        if not funcionario:
            raise ValueError("Funcionário não encontrado")
        if funcionario and funcionario.status == StatusFuncionario.PENDENTE:
            raise ValueError("Funcionário ainda não ativou a conta")

        if funcionario.status == StatusFuncionario.INATIVO:
            funcionario.status = StatusFuncionario.ATIVO
        else:
            funcionario.status = StatusFuncionario.INATIVO
        return self.repository.atualizar(funcionario)

    def apagar_funcionario(self, funcionario_id: int) -> None:
        funcionario = self.repository.buscar_por_id(funcionario_id)
        if not funcionario:
            raise ValueError("Funcionário não encontrado")

        self.repository.deletar(funcionario)
