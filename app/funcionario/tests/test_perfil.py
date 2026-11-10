from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.arquivo.model import Arquivo
from app.core.seguranca import hash_senha, verificar_senha


def _criar_png() -> bytes:
    imagem = Image.new("RGB", (10, 10), color="blue")
    conteudo = BytesIO()
    imagem.save(conteudo, format="PNG")
    return conteudo.getvalue()


def test_obter_perfil_exige_autenticacao(client: TestClient):
    resposta = client.get("/funcionarios/perfil")

    assert resposta.status_code == 401


def test_obter_perfil_retorna_dados_do_funcionario(
    client, token_admin, funcionario_admin, atuacao_padrao
):
    resposta = client.get(
        "/funcionarios/perfil", headers={"Authorization": f"Bearer {token_admin}"}
    )

    assert resposta.status_code == 200
    assert resposta.json()["funcionario_id"] == funcionario_admin.funcionario_id
    assert resposta.json()["email"] == funcionario_admin.email
    assert resposta.json()["atuacao"]["nome"] == atuacao_padrao.nome
    assert resposta.json()["foto_perfil_url"] is None
    assert "telefone" not in resposta.json()
    assert "senha_hash" not in resposta.json()


def test_editar_perfil_atualiza_nome_e_oab(client, db_session, token_admin, funcionario_admin):
    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "nome": "  Nome Atualizado  ",
            "uf_oab": "DF",
            "numero_oab": "12345",
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Nome Atualizado"
    assert resposta.json()["email"] == funcionario_admin.email
    assert resposta.json()["uf_oab"] == "DF"
    assert resposta.json()["numero_oab"] == "12345"
    db_session.refresh(funcionario_admin)
    assert funcionario_admin.nome == "Nome Atualizado"
    assert funcionario_admin.email == "admin.fixture@test.com"


def test_editar_perfil_rejeita_alteracao_de_email(
    client, db_session, token_admin, funcionario_admin
):
    email_original = funcionario_admin.email
    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"email": "novo.email@example.com"},
    )

    assert resposta.status_code == 422
    db_session.refresh(funcionario_admin)
    assert funcionario_admin.email == email_original


def test_editar_perfil_pode_limpar_dados_oab(client, db_session, token_admin, funcionario_admin):
    funcionario_admin.uf_oab = "DF"
    funcionario_admin.numero_oab = "12345"
    db_session.commit()

    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"uf_oab": None, "numero_oab": None},
    )

    assert resposta.status_code == 200
    assert resposta.json()["uf_oab"] is None
    assert resposta.json()["numero_oab"] is None


def test_editar_perfil_atualiza_area(
    client, db_session, token_admin, funcionario_admin, atuacao_padrao
):
    from app.atuacao.model import Atuacao

    nova_atuacao = Atuacao(nome="Direito Penal", descricao="Direito penal")
    db_session.add(nova_atuacao)
    db_session.commit()
    db_session.refresh(nova_atuacao)

    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"atuacao_id": nova_atuacao.atuacao_id},
    )

    assert resposta.status_code == 200
    assert resposta.json()["atuacao_id"] == nova_atuacao.atuacao_id
    assert resposta.json()["atuacao"]["nome"] == "Direito Penal"
    assert resposta.json()["nome"] == funcionario_admin.nome
    assert resposta.json()["email"] == funcionario_admin.email
    assert resposta.json()["atuacao_id"] != atuacao_padrao.atuacao_id


def test_editar_perfil_nao_aceita_area_inexistente(client, token_admin):
    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"atuacao_id": 9999},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Área de atuação não encontrada"


def test_editar_perfil_pode_remover_area(
    client, db_session, token_admin, funcionario_admin, atuacao_padrao
):
    funcionario_admin.atuacao_id = atuacao_padrao.atuacao_id
    db_session.commit()

    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"atuacao_id": None},
    )

    assert resposta.status_code == 200
    assert resposta.json()["atuacao_id"] is None
    assert resposta.json()["atuacao"] is None


def test_editar_perfil_valida_e_altera_senha(client, db_session, token_admin, funcionario_admin):
    senha_atual = "senhaAtual123"
    funcionario_admin.senha_hash = hash_senha(senha_atual)
    db_session.commit()

    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "senhaAtual": senha_atual,
            "novaSenha": "senhaNova123",
            "confirmarNovaSenha": "senhaNova123",
        },
    )

    assert resposta.status_code == 200
    db_session.refresh(funcionario_admin)
    assert verificar_senha("senhaNova123", funcionario_admin.senha_hash)


def test_editar_perfil_rejeita_senha_atual_incorreta(
    client, db_session, token_admin, funcionario_admin
):
    funcionario_admin.senha_hash = hash_senha("senhaCorreta123")
    db_session.commit()

    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "senhaAtual": "senhaErrada123",
            "novaSenha": "senhaNova123",
            "confirmarNovaSenha": "senhaNova123",
        },
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Senha atual incorreta"


def test_editar_perfil_rejeita_confirmacao_de_senha_diferente(client, token_admin):
    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "senhaAtual": "senhaAtual123",
            "novaSenha": "senhaNova123",
            "confirmarNovaSenha": "outraSenha123",
        },
    )

    assert resposta.status_code == 422


def test_atualizar_foto_perfil_salva_imagem_e_responde_url(
    client, db_session, token_admin, funcionario_admin, monkeypatch
):
    funcionario_admin.exibicao_institucional = True
    db_session.commit()
    monkeypatch.setattr("app.funcionario.service.salvar_arquivo", lambda **kwargs: "foto/nova.png")
    monkeypatch.setattr(
        "app.core.storage.obter_url_publica", lambda chave: f"https://exemplo/{chave}"
    )

    resposta = client.put(
        "/funcionarios/perfil/foto",
        headers={"Authorization": f"Bearer {token_admin}"},
        files={"file": ("perfil.png", _criar_png(), "image/png")},
    )

    assert resposta.status_code == 200
    assert resposta.json()["foto_perfil_url"] == "https://exemplo/foto/nova.png"
    db_session.refresh(funcionario_admin)
    arquivo = db_session.get(Arquivo, funcionario_admin.foto_perfil)
    assert arquivo is not None
    assert arquivo.origem == "funcionario"
    assert arquivo.funcionario_id == funcionario_admin.funcionario_id

    perfil = client.get("/funcionarios/perfil", headers={"Authorization": f"Bearer {token_admin}"})
    funcionarios = client.get("/funcionarios")
    equipe = client.get("/institucional/equipe")

    assert perfil.status_code == 200
    assert perfil.json()["foto_perfil_url"] == "https://exemplo/foto/nova.png"
    assert funcionarios.status_code == 200
    funcionario_listado = next(
        item
        for item in funcionarios.json()
        if item["funcionario_id"] == funcionario_admin.funcionario_id
    )
    assert funcionario_listado["foto_perfil_url"] == "https://exemplo/foto/nova.png"
    assert equipe.status_code == 200
    membro_equipe = next(item for item in equipe.json() if item["nome"] == funcionario_admin.nome)
    assert membro_equipe["foto_perfil_url"] == "https://exemplo/foto/nova.png"


def test_atualizar_foto_perfil_rejeita_arquivo_invalido(client, token_admin):
    resposta = client.put(
        "/funcionarios/perfil/foto",
        headers={"Authorization": f"Bearer {token_admin}"},
        files={"file": ("perfil.txt", b"nao e uma imagem", "text/plain")},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "A foto de perfil deve ser uma imagem JPG ou PNG válida"


def test_atualizar_foto_perfil_rejeita_arquivo_maior_que_limite(client, token_admin):
    resposta = client.put(
        "/funcionarios/perfil/foto",
        headers={"Authorization": f"Bearer {token_admin}"},
        files={"file": ("perfil.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "A foto de perfil deve ter no máximo 5MB"


def test_editar_perfil_rejeita_telefone_nao_suportado(client, token_admin):
    resposta = client.patch(
        "/funcionarios/perfil",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"telefone": "(61) 99999-9999"},
    )

    assert resposta.status_code == 422
