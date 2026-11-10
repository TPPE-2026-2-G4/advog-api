import filetype
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.arquivo.model import Arquivo
from app.arquivo.repository import ArquivoRepository
from app.atuacao.repository import AtuacaoRepository
from app.cargo.repository import CargoRepository
from app.core.seguranca import hash_senha, verificar_senha
from app.core.storage import remover_arquivo, salvar_arquivo
from app.funcionario.model import Funcionario, StatusFuncionario
from app.funcionario.repository import FuncionarioRepository
from app.funcionario.schema import (
    FuncionarioCreate,
    FuncionarioPerfilUpdate,
    FuncionarioPrimeiroAcesso,
    FuncionarioUpdate,
)

TAMANHO_MAXIMO_FOTO_PERFIL = 5 * 1024 * 1024


class FuncionarioService:
    def __init__(self, db_session: Session):
        self.repository = FuncionarioRepository(db_session)
        self.cargo_repository = CargoRepository(db_session)
        self.atuacao_repository = AtuacaoRepository(db_session)
        self.arquivo_repository = ArquivoRepository(db_session)

    def buscar_todos(self) -> list[Funcionario]:
        return self.repository.buscar_todos()

    def obter_perfil(self, funcionario_id: int) -> Funcionario:
        funcionario = self.repository.buscar_por_id(funcionario_id)
        if not funcionario:
            raise ValueError("Funcionário não encontrado")
        return funcionario

    def editar_perfil(self, funcionario_id: int, dados: FuncionarioPerfilUpdate) -> Funcionario:
        funcionario = self.obter_perfil(funcionario_id)
        campos_enviados = dados.model_fields_set

        if "nome" in campos_enviados and dados.nome is not None:
            funcionario.nome = dados.nome.strip()

        if "uf_oab" in campos_enviados:
            funcionario.uf_oab = dados.uf_oab

        if "numero_oab" in campos_enviados:
            funcionario.numero_oab = dados.numero_oab

        if "atuacao_id" in campos_enviados:
            if dados.atuacao_id is not None and not self.atuacao_repository.buscar_por_id(
                dados.atuacao_id
            ):
                raise ValueError("Área de atuação não encontrada")
            funcionario.atuacao_id = dados.atuacao_id

        if dados.nova_senha is not None:
            if not funcionario.senha_hash or not verificar_senha(
                dados.senha_atual or "", funcionario.senha_hash
            ):
                raise ValueError("Senha atual incorreta")
            funcionario.senha_hash = hash_senha(dados.nova_senha)

        return self.repository.atualizar(funcionario)

    def atualizar_foto_perfil(self, funcionario_id: int, file: UploadFile) -> Funcionario:
        funcionario = self.obter_perfil(funcionario_id)
        conteudo = file.file.read(TAMANHO_MAXIMO_FOTO_PERFIL + 1)
        if len(conteudo) > TAMANHO_MAXIMO_FOTO_PERFIL:
            raise ValueError("A foto de perfil deve ter no máximo 5MB")

        kind = filetype.guess(conteudo)
        if not kind or kind.extension not in ("jpg", "png"):
            raise ValueError("A foto de perfil deve ser uma imagem JPG ou PNG válida")

        file.file.seek(0)
        try:
            with Image.open(file.file) as imagem:
                imagem.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
            raise ValueError("A foto de perfil deve ser uma imagem JPG ou PNG válida") from e

        file.file.seek(0)
        content_type = "image/jpeg" if kind.extension == "jpg" else "image/png"
        chave = salvar_arquivo(
            conteudo=file.file,
            extensao=kind.extension,
            content_type=content_type,
            pasta="fotos-perfil",
        )

        arquivo_antigo = self.arquivo_repository.buscar_por_id(funcionario.foto_perfil)
        novo_arquivo = self.arquivo_repository.adicionar(
            Arquivo(
                nome_arquivo=(file.filename or f"foto-perfil.{kind.extension}")[:255],
                tipo_mime=content_type,
                tamanho_bytes=len(conteudo),
                bucket_link=chave,
                origem="funcionario",
                funcionario_id=funcionario_id,
            )
        )
        funcionario.foto_perfil = novo_arquivo.arquivo_id
        funcionario = self.repository.atualizar(funcionario)

        if arquivo_antigo and arquivo_antigo.origem == "funcionario":
            remover_arquivo(arquivo_antigo.bucket_link)
            self.arquivo_repository.deletar(arquivo_antigo)

        return funcionario

    def buscar_visiveis_institucional(self) -> list[Funcionario]:
        return self.repository.buscar_visiveis_institucional()

    def criar_funcionario(self, dados: FuncionarioCreate) -> Funcionario:
        if self.repository.buscar_por_email(dados.email.lower()):
            raise ValueError("Email já cadastrado")

        cargo = self.cargo_repository.buscar_por_id(dados.cargo_id)
        if not cargo:
            raise ValueError("Cargo não encontrado")

        if dados.atuacao_id is not None and not self.atuacao_repository.buscar_por_id(
            dados.atuacao_id
        ):
            raise ValueError("Área de atuação não encontrada")

        foto_padrao = self.arquivo_repository.obter_padrao()
        req = Funcionario(
            nome=dados.nome,
            email=dados.email.lower(),
            cargo_id=dados.cargo_id,
            atuacao_id=dados.atuacao_id,
            foto_perfil=foto_padrao.arquivo_id,
        )
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

    def mudar_receber_emails(self, funcionario_id: int, receber_emails: bool) -> Funcionario:
        funcionario = self.repository.buscar_por_id(funcionario_id)
        if not funcionario:
            raise ValueError("Funcionário não encontrado")

        funcionario.receber_emails = receber_emails
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
        if dados.receber_emails is not None:
            funcionario.receber_emails = dados.receber_emails

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
