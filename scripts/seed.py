# ruff: noqa: E402
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)

from app.arquivo.model import Arquivo  # noqa: E402
from app.arquivo.repository import ArquivoRepository  # noqa: E402
from app.atividade.model import Atividade  # noqa: E402, F401
from app.atuacao.model import Atuacao  # noqa: E402
from app.cargo.model import Cargo  # noqa: E402
from app.cargo.schema import PermissaoBase  # noqa: E402
from app.cliente.model import Cliente  # noqa: E402, F401
from app.config.database import Base, SessionLocal, engine  # noqa: E402
from app.core.seguranca import hash_senha  # noqa: E402
from app.core.storage import garantir_bucket, salvar_arquivo  # noqa: E402
from app.etapa_cliente.model import EtapaCliente  # noqa: E402
from app.etapa_kanban.model import EtapaKanban  # noqa: E402
from app.funcionario.model import Funcionario, StatusFuncionario  # noqa: E402
from app.institucional.model import Institucional  # noqa: E402
from app.processo.model import Processo  # noqa: E402, F401

ETAPAS_CLIENTE = (
    "Novo contato",
    "Atendimento iniciado",
    "Em negociação",
    "Cliente ativo",
    "Encerrado",
)

ETAPAS_KANBAN = ("Backlog", "Em Execução", "Revisão", "Finalizado")


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    Permissao = PermissaoBase(**{campo: True for campo in PermissaoBase.model_fields}).model_dump()
    db = SessionLocal()

    try:
        cargo = db.query(Cargo).filter_by(nome_cargo="Administrador").first()
        if cargo is None:
            cargo = Cargo(
                nome_cargo="Administrador",
                descricao="Cargo com todas as permissões",
                permissao=Permissao,
            )
            db.add(cargo)
            db.flush()
        else:
            cargo.permissao = Permissao

        atuacoes = db.query(Atuacao).all()
        if not atuacoes:
            atuacoes = [
                Atuacao(
                    atuacao_id=1,
                    nome="Direito Trabalhista",
                    descricao="Representação em reclamações trabalhistas, acordos, rescisões e defesas patronais.",
                    exibicao_institucional=True,
                ),
                Atuacao(
                    atuacao_id=2,
                    nome="Direito Civil",
                    descricao="Ações de indenização, contratos, usucapião, família e sucessões.",
                    exibicao_institucional=True,
                ),
                Atuacao(
                    atuacao_id=3,
                    nome="Direito Previdenciário",
                    descricao="Aposentadorias, benefícios por incapacidade, pensões e revisões de benefícios.",
                    exibicao_institucional=True,
                ),
                Atuacao(
                    atuacao_id=4,
                    nome="Direito Tributário",
                    descricao="Planejamento fiscal, execuções fiscais, mandados de segurança e consultoria tributária.",
                    exibicao_institucional=True,
                ),
            ]
            db.add_all(atuacoes)
            print("Áreas de atuação criadas com sucesso.")
        else:
            print("Áreas de atuação já existem.")

        db.flush()
        arquivo_padrao = ArquivoRepository(db).obter_padrao()

        email = os.getenv("ADMIN_EMAIL")
        senha = os.getenv("ADMIN_PASSWORD")
        if not email or not senha:
            raise SystemExit(
                "As variáveis de ambiente ADMIN_EMAIL e ADMIN_PASSWORD devem ser definidas."
            )
        admin = db.query(Funcionario).filter_by(email=email).first()
        if admin is None:
            admin = Funcionario(
                nome="Administrador",
                email=email,
                senha_hash=hash_senha(senha),
                status=StatusFuncionario.ATIVO,
                cargo_id=cargo.cargo_id,
                atuacao_id=atuacoes[0].atuacao_id,
                foto_perfil=arquivo_padrao.arquivo_id,
            )
            db.add(admin)
            print(f"Usuário administrador criado com sucesso: {email}")
        else:
            print(f"Usuário administrador já existe: {email}")

        institucional = db.query(Institucional).first()
        if institucional is None:
            arquivo_imagem_sobre = arquivo_padrao
            caminho_imagem = Path(__file__).parent / "assets" / "default_sobre.jpg"
            if caminho_imagem.exists():
                garantir_bucket()
                with open(caminho_imagem, "rb") as f:
                    chave_imagem_sobre = salvar_arquivo(
                        conteudo=f, extensao="jpg", content_type="image/jpeg", pasta="sobre"
                    )
                arquivo_imagem_sobre = Arquivo(
                    nome_arquivo=caminho_imagem.name,
                    tipo_mime="image/jpeg",
                    tamanho_bytes=caminho_imagem.stat().st_size,
                    bucket_link=chave_imagem_sobre,
                    origem="sistema",
                )
                db.add(arquivo_imagem_sobre)
                db.flush()

            institucional = Institucional(
                institucional_id=1,
                nome_escritorio="Carreiro Advocacia",
                descricao="Tradição e excelência na defesa dos seus direitos, com foco absoluto em resultados e segurança jurídica.",
                sobre_escritorio=(
                    "Fundado em 2010 por Dr. Alexandre Carreiro, o escritório nasceu com a missão "
                    "de oferecer atendimento jurídico de excelência, combinando tradição e inovação tecnológica. "
                    "Localizado em Brasília-DF, atendemos clientes em todo o território nacional.\n\n"
                    "Com mais de 15 anos de experiência, nossa equipe é formada por advogados especializados que "
                    "priorizam a defesa dos direitos dos nossos clientes com ética, dedicação e resultados concretos. "
                    "Nosso maior diferencial é o controle rigoroso de prazos processuais, garantindo que nenhuma "
                    "oportunidade seja perdida."
                ),
                email="contato@carreiro.adv.br",
                telefone="(99) 99999-9999",
                endereco="SCLN 203, Bloco B — Brasília, DF",
                imagem_logotipo=arquivo_padrao.arquivo_id,
                banner_hero=arquivo_padrao.arquivo_id,
                imagem_sobre_escritorio=arquivo_imagem_sobre.arquivo_id,
            )
            db.add(institucional)
            print("Informações institucionais criadas com sucesso.")
        else:
            print("Informações institucionais já existem.")

        nomes_kanban_existentes = {etapa.nome for etapa in db.query(EtapaKanban)}
        db.add_all(
            EtapaKanban(nome=nome, ordem=ordem)
            for ordem, nome in enumerate(ETAPAS_KANBAN, start=1)
            if nome not in nomes_kanban_existentes
        )

        etapas_existentes = {etapa.etapa_id for etapa in db.query(EtapaCliente)}
        db.add_all(
            EtapaCliente(etapa_id=etapa_id, nome_etapa=nome)
            for etapa_id, nome in enumerate(ETAPAS_CLIENTE, start=1)
            if etapa_id not in etapas_existentes
        )

        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed()
