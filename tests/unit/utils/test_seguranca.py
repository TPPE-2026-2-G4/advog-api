from app.utils.seguranca import hash_senha, verificar_senha

def test_hash_senha_gera_hash_diferente_da_senha_original():
  senha = "pytest123"
  senha_hash = hash_senha(senha)

  assert senha != senha_hash
  assert senha_hash.startswith("$2b$")

def test_hash_senha_gera_hash_diferente_para_senhas_iguais():
  senha = "pytest123"
  
  assert hash_senha(senha) != hash_senha(senha)

def test_verificar_senha_retorna_true_para_senha_correta():
  senha = "pytest123"
  senha_hash = hash_senha(senha)

  assert verificar_senha(senha, senha_hash) is True

def test_verificar_senha_retorna_false_para_senha_incorreta():
  senha = "pytest123"
  senha_hash = hash_senha(senha)

  assert verificar_senha("senha_incorreta", senha_hash) is False