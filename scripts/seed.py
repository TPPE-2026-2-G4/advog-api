import os

from dotenv import load_dotenv

from app.cargo.model import Cargo
from app.cargo.schema import PermissaoBase
from app.config.database import Base, SessionLocal, engine
from app.core.seguranca import hash_senha
from app.funcionario.model import Funcionario, StatusFuncionario

load_dotenv()
load_dotenv(".env.local", override=True)


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

        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed()
