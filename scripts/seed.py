import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)

from app.cargo.model import Cargo  # noqa: E402
from app.cargo.schema import PermissaoBase  # noqa: E402
from app.config.database import Base, SessionLocal, engine  # noqa: E402
from app.core.seguranca import hash_senha  # noqa: E402
from app.core.storage import garantir_bucket, salvar_arquivo  # noqa: E402
from app.funcionario.model import Funcionario, StatusFuncionario  # noqa: E402
from app.institucional.model import Institucional  # noqa: E402


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
            )
            db.add(admin)
            print(f"Usuário administrador criado com sucesso: {email}")
        else:
            print(f"Usuário administrador já existe: {email}")

        institucional = db.query(Institucional).first()
        if institucional is None:
            chave_imagem_sobre = None
            caminho_imagem = Path(__file__).parent / "assets" / "default_sobre.jpg"
            if caminho_imagem.exists():
                garantir_bucket()
                with open(caminho_imagem, "rb") as f:
                    chave_imagem_sobre = salvar_arquivo(
                        conteudo=f,
                        extensao="jpg",
                        content_type="image/jpeg",
                        pasta="sobre"
                    )

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
                texto_adicional_sobre="Texto adicional que deverá tirar do banco",
                imagem_sobre=chave_imagem_sobre,
            )
            db.add(institucional)
            print("Informações institucionais criadas com sucesso.")
        else:
            print("Informações institucionais já existem.")

        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed()
