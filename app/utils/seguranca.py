from passlib.context import CryptContext

pwd_context = CryptContext(
  schemes=["bcrypt"],
  deprecated="auto",
  argon2__type="ID",
  argon2__memory_cost=19456,
  argon2__time_cost=2,
  argon2__parallelism=1,
)

def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha, senha_hash)