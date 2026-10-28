from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.cargo.model import Cargo
from app.cliente.model import Cliente
from app.funcionario.model import Funcionario, StatusFuncionario
from app.processo.model import Processo, StatusProcesso


def criar_cargo(
    db: Session,
    permissoes: dict[str, bool] | None = None,
) -> Cargo:
    cargo = Cargo(
        nome_cargo="Cargo de Teste",
        descricao="Cargo utilizado nos testes",
        permissao=permissoes or {},
    )

    db.add(cargo)
    db.commit()
    db.refresh(cargo)

    return cargo


def criar_funcionario(
    db: Session,
    cargo: Cargo,
    email: str,
) -> Funcionario:
    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Funcionário de Teste",
        email=email,
        status=StatusFuncionario.ATIVO,
        cargo_id=cargo.cargo_id,
    )

    db.add(funcionario)
    db.commit()
    db.refresh(funcionario)

    return funcionario


def criar_cliente(db: Session) -> Cliente:
    cliente = Cliente(
        nome="Cliente de Teste",
        telefone="61999999999",
        email="cliente.processo@test.com",
        area_interesse="Civil",
        ultima_interacao=datetime(2026, 1, 1),
        responsavel_id=None,
        etapa_id=1,
    )

    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    return cliente


def criar_processo(
    db: Session,
    cliente_id: int,
    funcionario_id: int = 1,
    cnj: str = "11111111111111111111",
) -> Processo:
    processo = Processo(
        cnj=cnj,
        titulo="Processo de Teste",
        descricao="Descrição do processo de teste",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        cliente_id=cliente_id,
        funcionario_id=funcionario_id,
    )

    db.add(processo)
    db.commit()
    db.refresh(processo)

    return processo


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def cliente_processo(db_session):
    return criar_cliente(db_session)


@pytest.fixture()
def funcionario_responsavel(db_session):
    cargo = criar_cargo(db_session)

    return criar_funcionario(
        db_session,
        cargo,
        "responsavel.processo@test.com",
    )


@pytest.fixture()
def usuario_processos(db_session, token_acesso):
    cargo = criar_cargo(
        db_session,
        {
            "visualizar_processos": True,
            "criar_processos": True,
            "editar_processos": True,
            "excluir_processos": True,
        },
    )

    funcionario = criar_funcionario(
        db_session,
        cargo,
        "usuario.processos@test.com",
    )

    token = token_acesso(
        funcionario.funcionario_id,
        funcionario.email,
    )

    return funcionario, token


def test_listar_processos(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
    funcionario_responsavel,
):
    _, token = usuario_processos

    processo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
        funcionario_id=funcionario_responsavel.funcionario_id,
    )

    response = client.get(
        "/processos/",
        headers=auth_header(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["itens"]) == 1
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1

    processo_data = data["itens"][0]

    assert processo_data["processo_id"] == processo.processo_id
    assert processo_data["cnj"] == processo.cnj
    assert processo_data["titulo"] == processo.titulo
    assert processo_data["status"] == "Ativo"
    assert processo_data["cliente_id"] == cliente_processo.cliente_id
    assert processo_data["funcionario_id"] == funcionario_responsavel.funcionario_id


def test_listar_processos_sem_autenticacao(client):
    response = client.get("/processos/")

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("parametro", "valor"),
    [
        ("status", "Ativo"),
        ("cnj", "111111111111"),
        ("titulo", "Processo"),
        ("descricao", "Descrição"),
        ("tribunal", "TJSP"),
        ("area", "Civil"),
    ],
)
def test_filtrar_processos(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
    parametro,
    valor,
):
    _, token = usuario_processos

    processo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
    )

    response = client.get(
        "/processos/",
        params={parametro: valor},
        headers=auth_header(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["itens"]) == 1
    assert data["total"] == 1
    assert data["itens"][0]["processo_id"] == processo.processo_id


@pytest.mark.parametrize(
    ("parametro", "valor"),
    [
        ("processo_id", "processo_id"),
        ("cliente_id", "cliente_id"),
    ],
)
def test_filtrar_processos_por_id(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
    parametro,
    valor,
):
    _, token = usuario_processos

    processo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
    )

    valores = {
        "processo_id": processo.processo_id,
        "cliente_id": processo.cliente_id,
    }

    response = client.get(
        "/processos/",
        params={parametro: valores[valor]},
        headers=auth_header(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["itens"]) == 1
    assert data["total"] == 1
    assert data["itens"][0]["processo_id"] == processo.processo_id


def test_filtrar_por_funcionario(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
    funcionario_responsavel,
):
    _, token = usuario_processos

    processo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
        funcionario_id=funcionario_responsavel.funcionario_id,
    )

    response = client.get(
        "/processos/",
        params={"funcionario_id": funcionario_responsavel.funcionario_id},
        headers=auth_header(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["itens"]) == 1
    assert data["itens"][0]["processo_id"] == processo.processo_id


def test_filtrar_processos_sem_resultado(
    client,
    usuario_processos,
):
    _, token = usuario_processos

    response = client.get(
        "/processos/",
        params={"titulo": "Processo Inexistente"},
        headers=auth_header(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["itens"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1


def test_criar_processo(
    client,
    usuario_processos,
    cliente_processo,
    funcionario_responsavel,
):
    _, token = usuario_processos

    payload = {
        "cnj": "22222222222222222222",
        "titulo": "Novo Processo",
        "descricao": "Descrição do novo processo",
        "status": "Em Análise",
        "tribunal": "TRF1",
        "area": "Tributária",
        "data_inicio": "2026-03-01T00:00:00",
        "data_prazo": "2026-12-31T00:00:00",
        "cliente_id": cliente_processo.cliente_id,
        "funcionario_id": funcionario_responsavel.funcionario_id,
    }

    response = client.post(
        "/processos/",
        json=payload,
        headers=auth_header(token),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["cnj"] == payload["cnj"]
    assert data["titulo"] == payload["titulo"]
    assert data["status"] == "Em Análise"
    assert data["cliente_id"] == cliente_processo.cliente_id
    assert data["funcionario_id"] == funcionario_responsavel.funcionario_id
    assert "processo_id" in data


def test_criar_processo_sem_cliente(
    client,
    usuario_processos,
):
    _, token = usuario_processos

    payload = {
        "cnj": "33333333333333333333",
        "titulo": "Processo Sem Cliente",
        "status": "Ativo",
        "tribunal": "TJSP",
        "area": "Civil",
    }

    response = client.post(
        "/processos/",
        json=payload,
        headers=auth_header(token),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("campo", ["descricao", "data_inicio", "data_prazo", "funcionario_id"])
def test_criar_processo_sem_campo_obrigatorio_retorna_422(
    client,
    usuario_processos,
    cliente_processo,
    funcionario_responsavel,
    campo,
):
    _, token = usuario_processos

    payload = {
        "cnj": "44444444444444444444",
        "titulo": "Processo Incompleto",
        "descricao": "Descrição",
        "status": "Ativo",
        "tribunal": "TJSP",
        "area": "Civil",
        "data_inicio": "2026-03-01T00:00:00",
        "data_prazo": "2026-12-31T00:00:00",
        "cliente_id": cliente_processo.cliente_id,
        "funcionario_id": funcionario_responsavel.funcionario_id,
    }
    del payload[campo]

    response = client.post("/processos/", json=payload, headers=auth_header(token))

    assert response.status_code == 422


def test_criar_processo_com_cnj_duplicado(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
):
    _, token = usuario_processos

    criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
        cnj="55555555555555555555",
    )

    payload = {
        "cnj": "55555555555555555555",
        "titulo": "Processo Duplicado",
        "descricao": "Descrição",
        "status": "Ativo",
        "tribunal": "TJSP",
        "area": "Civil",
        "data_inicio": "2026-03-01T00:00:00",
        "data_prazo": "2026-12-31T00:00:00",
        "cliente_id": cliente_processo.cliente_id,
        "funcionario_id": 1,
    }

    response = client.post(
        "/processos/",
        json=payload,
        headers=auth_header(token),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Processo já cadastrado"


def test_atualizar_processo(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
):
    _, token = usuario_processos

    processo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
    )

    response = client.patch(
        f"/processos/{processo.processo_id}",
        json={
            "titulo": "Título Atualizado",
            "status": "Concluído",
        },
        headers=auth_header(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["processo_id"] == processo.processo_id
    assert data["titulo"] == "Título Atualizado"
    assert data["status"] == "Concluído"


def test_atualizar_processo_parcialmente(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
):
    _, token = usuario_processos

    processo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
    )

    response = client.patch(
        f"/processos/{processo.processo_id}",
        json={"status": "Arquivado"},
        headers=auth_header(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "Arquivado"
    assert data["titulo"] == processo.titulo
    assert data["cliente_id"] == processo.cliente_id


def test_atualizar_funcionario(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
    funcionario_responsavel,
):
    _, token = usuario_processos

    processo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
    )

    response = client.patch(
        f"/processos/{processo.processo_id}",
        json={
            "funcionario_id": funcionario_responsavel.funcionario_id,
        },
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["funcionario_id"] == funcionario_responsavel.funcionario_id


def test_atualizar_processo_inexistente(
    client,
    usuario_processos,
):
    _, token = usuario_processos

    response = client.patch(
        "/processos/999999",
        json={"titulo": "Teste"},
        headers=auth_header(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Processo não encontrado"


def test_atualizar_processo_com_cnj_duplicado(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
):
    _, token = usuario_processos

    primeiro = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
        cnj="66666666666666666666",
    )

    segundo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
        cnj="77777777777777777777",
    )

    response = client.patch(
        f"/processos/{segundo.processo_id}",
        json={"cnj": primeiro.cnj},
        headers=auth_header(token),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "CNJ já cadastrado"


def test_deletar_processo(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
):
    _, token = usuario_processos

    processo = criar_processo(
        db_session,
        cliente_id=cliente_processo.cliente_id,
    )

    response = client.delete(
        f"/processos/{processo.processo_id}",
        headers=auth_header(token),
    )

    assert response.status_code == 204
    assert response.content == b""

    assert db_session.get(Processo, processo.processo_id) is None


def test_deletar_processo_inexistente(
    client,
    usuario_processos,
):
    _, token = usuario_processos

    response = client.delete(
        "/processos/999999",
        headers=auth_header(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Processo não encontrado"


@pytest.mark.parametrize(
    "dias_param,func_filtro,espera_critico",
    [
        (None, None, True),
        (10, None, True),
        (500, None, False),
        (30, True, True),
        (30, 99999, False),
    ],
)
def test_listar_processos_criticos_parametrizado(
    client,
    db_session,
    usuario_processos,
    cliente_processo,
    funcionario_responsavel,
    dias_param,
    func_filtro,
    espera_critico,
):
    _, token = usuario_processos

    proc = Processo(
        data_prazo=datetime(2026, 12, 31),
        cnj="88888888888888888888",
        titulo="Processo Crítico Controller",
        descricao="Desc",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        data_inicio=datetime.now(UTC) - timedelta(days=40),
        data_realizado=None,
        cliente_id=cliente_processo.cliente_id,
        funcionario_id=funcionario_responsavel.funcionario_id,
    )
    db_session.add(proc)
    db_session.commit()
    db_session.refresh(proc)

    url = "/processos/criticos/"
    params = []
    if dias_param is not None:
        params.append(f"dias_sem_movimentacao={dias_param}")
    if func_filtro is True:
        params.append(f"funcionario_id={funcionario_responsavel.funcionario_id}")
    elif func_filtro is not None:
        params.append(f"funcionario_id={func_filtro}")

    if params:
        url += "?" + "&".join(params)

    response = client.get(url, headers=auth_header(token))

    assert response.status_code == 200
    dados = response.json()
    cnjs = [p["cnj"] for p in dados]

    if espera_critico:
        assert "88888888888888888888" in cnjs
    else:
        assert "88888888888888888888" not in cnjs


def test_listar_processos_criticos_sem_permissao(
    client,
    db_session,
    cliente_processo,
    token_acesso,
):
    cargo_sem_permissao = criar_cargo(db_session, {"visualizar_processos": False})
    usuario = criar_funcionario(db_session, cargo_sem_permissao, "sem.perm@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get("/processos/criticos/", headers=auth_header(token))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_sincronizar_processos_controller_sucesso(
    client,
    db_session,
    token_acesso,
):
    from unittest.mock import patch

    cargo = criar_cargo(db_session, {"editar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "sync.admin@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    with patch(
        "app.processo.service.ProcessoService.sincronizar_processos_com_api", return_value=3
    ):
        response = client.post("/processos/sincronizar", headers=auth_header(token))

    assert response.status_code == 200
    dados = response.json()
    assert dados["atualizados"] == 3
    assert "3 processos sincronizados" in dados["mensagem"]


@pytest.mark.asyncio
async def test_sincronizar_processos_controller_erro(
    client,
    db_session,
    token_acesso,
):
    from unittest.mock import patch

    cargo = criar_cargo(db_session, {"editar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "sync.erro@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    with patch(
        "app.processo.service.ProcessoService.sincronizar_processos_com_api",
        side_effect=Exception("Falha de conexão"),
    ):
        response = client.post("/processos/sincronizar", headers=auth_header(token))

    assert response.status_code == 500
    assert "Falha ao sincronizar processos com a API do Datajud" in response.json()["detail"]


def test_upload_documento_sem_token(client):
    response = client.post("/processos/1/documentos")
    assert response.status_code == 401


def test_upload_documento_sem_permissao(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"editar_processos": False})
    usuario = criar_funcionario(db_session, cargo, "semperm.doc@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.post("/processos/1/documentos", headers=auth_header(token))
    assert response.status_code == 403


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_upload_documento_sucesso(
    mock_url, mock_salvar, client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"editar_processos": True, "visualizar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "comperm.doc@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    proc = criar_processo(db_session, cliente_processo.cliente_id, cnj="11111222223333344444")

    mock_salvar.return_value = f"processos/{proc.processo_id}/arquivo.pdf"
    mock_url.return_value = "http://minio/doc.pdf"

    pdf_bytes = b"%PDF-1.4\n%conteudo de teste"
    response = client.post(
        f"/processos/{proc.processo_id}/documentos",
        headers=auth_header(token),
        files={"file": ("peticao.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    dados = response.json()
    assert dados["nome_original"] == "peticao.pdf"
    assert dados["origem"] == "manual"
    assert dados["processo_id"] == proc.processo_id
    assert dados["funcionario_id"] == usuario.funcionario_id
    assert dados["url"] == "http://minio/doc.pdf"


def test_upload_documento_processo_inexistente(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"editar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "proc.inex@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    pdf_bytes = b"%PDF-1.4\n%conteudo"
    response = client.post(
        "/processos/99999/documentos",
        headers=auth_header(token),
        files={"file": ("peticao.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 404
    assert "Processo não encontrado" in response.json()["detail"]


def test_upload_documento_arquivo_invalido(client, db_session, token_acesso, cliente_processo):
    cargo = criar_cargo(db_session, {"editar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "arquivo.inv@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    proc = criar_processo(db_session, cliente_processo.cliente_id, cnj="99999888887777766666")

    response = client.post(
        f"/processos/{proc.processo_id}/documentos",
        headers=auth_header(token),
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Extensão de arquivo não permitida" in response.json()["detail"]


def test_listar_documentos_controller_sem_permissao(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"visualizar_processos": False})
    usuario = criar_funcionario(db_session, cargo, "list.semperm@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get("/processos/1/documentos", headers=auth_header(token))
    assert response.status_code == 403


def test_listar_documentos_processo_inexistente(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"visualizar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "list.inex@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get("/processos/99999/documentos", headers=auth_header(token))
    assert response.status_code == 404
    assert "Processo não encontrado" in response.json()["detail"]


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_listar_documentos_sucesso(
    mock_url, mock_salvar, client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"editar_processos": True, "visualizar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "list.ok@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    proc = criar_processo(db_session, cliente_processo.cliente_id, cnj="77777666665555544444")

    mock_salvar.return_value = f"processos/{proc.processo_id}/doc.pdf"
    mock_url.return_value = "http://minio/doc.pdf"

    # Faz upload de um documento
    client.post(
        f"/processos/{proc.processo_id}/documentos",
        headers=auth_header(token),
        files={"file": ("peticao.pdf", b"%PDF-1.4\n%content", "application/pdf")},
    )

    response = client.get(f"/processos/{proc.processo_id}/documentos", headers=auth_header(token))
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["nome_original"] == "peticao.pdf"


def test_obter_url_documento_controller_erro(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"visualizar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "url.erro@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get("/processos/1/documentos/99999/url", headers=auth_header(token))
    assert response.status_code == 404
    assert "Documento não encontrado" in response.json()["detail"]


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_obter_url_documento_controller_sucesso(
    mock_url, mock_salvar, client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"editar_processos": True, "visualizar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "url.ok@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    proc = criar_processo(db_session, cliente_processo.cliente_id, cnj="55555444443333322222")
    mock_salvar.return_value = f"processos/{proc.processo_id}/doc.pdf"
    mock_url.return_value = "http://minio/presigned-url"

    up_res = client.post(
        f"/processos/{proc.processo_id}/documentos",
        headers=auth_header(token),
        files={"file": ("doc.pdf", b"%PDF-1.4\n%content", "application/pdf")},
    )
    doc_id = up_res.json()["documento_id"]

    response = client.get(
        f"/processos/{proc.processo_id}/documentos/{doc_id}/url?expiracao_segundos=900",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    dados = response.json()
    assert dados["documento_id"] == doc_id
    assert dados["url"] == "http://minio/presigned-url"
    assert dados["expira_em_segundos"] == 900


def test_deletar_documento_controller_erro(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"editar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "del.erro@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.delete("/processos/1/documentos/99999", headers=auth_header(token))
    assert response.status_code == 404
    assert "Documento não encontrado" in response.json()["detail"]


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.remover_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_deletar_documento_controller_sucesso(
    mock_url, mock_remover, mock_salvar, client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"editar_processos": True, "visualizar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "del.ok@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    proc = criar_processo(db_session, cliente_processo.cliente_id, cnj="33333222221111100000")
    mock_salvar.return_value = f"processos/{proc.processo_id}/doc.pdf"
    mock_url.return_value = "http://minio/doc.pdf"

    up_res = client.post(
        f"/processos/{proc.processo_id}/documentos",
        headers=auth_header(token),
        files={"file": ("doc.pdf", b"%PDF-1.4\n%content", "application/pdf")},
    )
    doc_id = up_res.json()["documento_id"]

    del_res = client.delete(
        f"/processos/{proc.processo_id}/documentos/{doc_id}",
        headers=auth_header(token),
    )
    assert del_res.status_code == 204

    # Confirma que documento não é mais listado
    list_res = client.get(f"/processos/{proc.processo_id}/documentos", headers=auth_header(token))
    assert list_res.json() == []


@pytest.mark.parametrize(
    "eh_admin,filtrar_outro_advogado,esperado_total,esperado_em_andamento,esperado_em_analise,esperado_finalizados,esperado_proximos,esperado_atrasados",
    [
        (True, False, 4, 2, 1, 1, 1, 1),
        (True, True, 1, 1, 0, 0, 0, 0),
        (False, False, 3, 1, 1, 1, 1, 1),
        (False, True, 3, 1, 1, 1, 1, 1),
    ],
)
def test_obter_resumo_processos_controller_parametrizado(
    client,
    db_session,
    cliente_processo,
    token_acesso,
    eh_admin,
    filtrar_outro_advogado,
    esperado_total,
    esperado_em_andamento,
    esperado_em_analise,
    esperado_finalizados,
    esperado_proximos,
    esperado_atrasados,
):
    nome_cargo = "Administrador" if eh_admin else "Advogado Associado"
    permissoes = {
        "visualizar_processos": True,
        "configuracoes_sistema": eh_admin,
    }
    cargo_usuario = Cargo(
        nome_cargo=nome_cargo,
        descricao="Cargo para teste de resumo",
        permissao=permissoes,
    )
    cargo_outro = Cargo(
        nome_cargo="Advogado",
        descricao="Outro cargo",
        permissao={"visualizar_processos": True},
    )
    db_session.add_all([cargo_usuario, cargo_outro])
    db_session.commit()
    db_session.refresh(cargo_usuario)
    db_session.refresh(cargo_outro)

    usuario = criar_funcionario(db_session, cargo_usuario, "usuario.resumo@test.com")
    outro_advogado = criar_funcionario(db_session, cargo_outro, "outro.resumo@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    hoje = datetime.now(UTC).date()
    processos_seed = [
        (
            "30000000000000000001",
            StatusProcesso.ATIVO,
            usuario.funcionario_id,
            datetime.combine(hoje - timedelta(days=2), datetime.min.time()),
        ),
        (
            "30000000000000000002",
            StatusProcesso.EM_ANALISE,
            usuario.funcionario_id,
            datetime.combine(hoje + timedelta(days=3), datetime.min.time()),
        ),
        (
            "30000000000000000003",
            StatusProcesso.CONCLUIDO,
            usuario.funcionario_id,
            datetime.combine(hoje - timedelta(days=5), datetime.min.time()),
        ),
        (
            "30000000000000000004",
            StatusProcesso.ATIVO,
            outro_advogado.funcionario_id,
            datetime.combine(hoje + timedelta(days=20), datetime.min.time()),
        ),
        (
            "30000000000000000005",
            StatusProcesso.ARQUIVADO,
            outro_advogado.funcionario_id,
            datetime.combine(hoje - timedelta(days=1), datetime.min.time()),
        ),
    ]
    for cnj, status_proc, func_id, data_prazo in processos_seed:
        db_session.add(
            Processo(
                descricao="Descrição",
                data_inicio=datetime(2026, 1, 1),
                cnj=cnj,
                titulo=f"Proc Resumo {cnj}",
                status=status_proc,
                tribunal="TJDFT",
                area="Civil",
                cliente_id=cliente_processo.cliente_id,
                funcionario_id=func_id,
                data_prazo=data_prazo,
            )
        )
    db_session.commit()

    params = {}
    if filtrar_outro_advogado:
        params["funcionario_id"] = outro_advogado.funcionario_id

    response = client.get(
        "/processos/resumo",
        params=params,
        headers=auth_header(token),
    )

    assert response.status_code == 200
    dados = response.json()
    assert dados["total"] == esperado_total
    assert dados["em_andamento"] == esperado_em_andamento
    assert dados["em_analise"] == esperado_em_analise
    assert dados["finalizados"] == esperado_finalizados
    assert dados["proximos_do_prazo"] == esperado_proximos
    assert dados["atrasados"] == esperado_atrasados


def test_obter_resumo_processos_sem_autenticacao_e_sem_permissao(
    client,
    db_session,
    token_acesso,
):
    resp_401 = client.get("/processos/resumo")
    assert resp_401.status_code == 401

    cargo_sem_perm = criar_cargo(db_session, {"visualizar_processos": False})
    usuario = criar_funcionario(db_session, cargo_sem_perm, "sem.perm.resumo@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    resp_403 = client.get("/processos/resumo", headers=auth_header(token))
    assert resp_403.status_code == 403


@pytest.mark.parametrize("campo", ["descricao", "data_inicio", "data_prazo", "funcionario_id"])
def test_atualizar_processo_campo_obrigatorio_nulo_retorna_422(
    client, db_session, usuario_processos, cliente_processo, funcionario_responsavel, campo
):
    _, token = usuario_processos
    processo = criar_processo(
        db_session, cliente_processo.cliente_id, funcionario_responsavel.funcionario_id
    )

    response = client.patch(
        f"/processos/{processo.processo_id}", json={campo: None}, headers=auth_header(token)
    )

    assert response.status_code == 422
