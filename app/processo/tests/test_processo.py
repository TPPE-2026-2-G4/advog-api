import io
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from openpyxl import load_workbook
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.arquivo.model import Arquivo
from app.cargo.model import Cargo
from app.cliente.model import Cliente
from app.config.database import Base, SessionLocal, engine
from app.funcionario.model import Funcionario, StatusFuncionario
from app.processo.model import Processo, StatusProcesso
from app.processo.repository import ProcessoRepository
from app.processo.schema import (
    DocumentoProcessoResponse,
    DocumentoUrlResponse,
    ProcessoCreate,
    ProcessoFilter,
    ProcessoResponse,
    ProcessoUpdate,
)
from app.processo.service import ProcessoService
from app.processo_arquivo.model import ProcessoArquivo
from app.processo_movimentacao.model import ProcessoMovimentacao, TipoMovimentacaoProcesso


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
            "gerenciar_processos": True,
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


def test_controller_listar_processos(
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


def test_controller_listar_processos_sem_autenticacao(client):
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
def test_controller_filtrar_processos(
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
def test_controller_filtrar_processos_por_id(
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


def test_controller_filtrar_por_funcionario(
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


def test_controller_filtrar_processos_sem_resultado(
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


def test_controller_criar_processo(
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


def test_controller_criar_processo_sem_cliente(
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
def test_controller_criar_processo_sem_campo_obrigatorio_retorna_422(
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


def test_controller_criar_processo_com_cnj_duplicado(
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


def test_controller_atualizar_processo(
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


def test_controller_atualizar_processo_parcialmente(
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


def test_controller_atualizar_funcionario(
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


def test_controller_atualizar_processo_inexistente(
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


def test_controller_atualizar_processo_com_cnj_duplicado(
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


def test_controller_deletar_processo(
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


def test_controller_deletar_processo_inexistente(
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
def test_controller_listar_processos_criticos_parametrizado(
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


def test_controller_listar_processos_criticos_sem_permissao(
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
async def test_controller_sincronizar_processos_controller_sucesso(
    client,
    db_session,
    token_acesso,
):
    from unittest.mock import patch

    cargo = criar_cargo(db_session, {"gerenciar_processos": True})
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
async def test_controller_sincronizar_processos_controller_erro(
    client,
    db_session,
    token_acesso,
):
    from unittest.mock import patch

    cargo = criar_cargo(db_session, {"gerenciar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "sync.erro@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    with patch(
        "app.processo.service.ProcessoService.sincronizar_processos_com_api",
        side_effect=Exception("Falha de conexão"),
    ):
        response = client.post("/processos/sincronizar", headers=auth_header(token))

    assert response.status_code == 500
    assert "Falha ao sincronizar processos com a API do Datajud" in response.json()["detail"]


def test_controller_upload_documento_sem_token(client):
    response = client.post("/processos/1/documentos")
    assert response.status_code == 401


def test_controller_upload_documento_sem_permissao(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"gerenciar_processos": False})
    usuario = criar_funcionario(db_session, cargo, "semperm.doc@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.post("/processos/1/documentos", headers=auth_header(token))
    assert response.status_code == 403


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_controller_upload_documento_sucesso(
    mock_url, mock_salvar, client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"gerenciar_processos": True, "visualizar_processos": True})
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


def test_controller_upload_documento_processo_inexistente(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"gerenciar_processos": True})
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


def test_controller_upload_documento_arquivo_invalido(
    client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"gerenciar_processos": True})
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


def test_controller_listar_documentos_controller_sem_permissao(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"visualizar_processos": False})
    usuario = criar_funcionario(db_session, cargo, "list.semperm@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get("/processos/1/documentos", headers=auth_header(token))
    assert response.status_code == 403


def test_controller_listar_documentos_processo_inexistente(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"visualizar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "list.inex@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get("/processos/99999/documentos", headers=auth_header(token))
    assert response.status_code == 404
    assert "Processo não encontrado" in response.json()["detail"]


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_controller_listar_documentos_sucesso(
    mock_url, mock_salvar, client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"gerenciar_processos": True, "visualizar_processos": True})
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


def test_controller_obter_url_documento_controller_erro(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"visualizar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "url.erro@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get("/processos/1/documentos/99999/url", headers=auth_header(token))
    assert response.status_code == 404
    assert "Documento não encontrado" in response.json()["detail"]


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_controller_obter_url_documento_controller_sucesso(
    mock_url, mock_salvar, client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"gerenciar_processos": True, "visualizar_processos": True})
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


def test_controller_deletar_documento_controller_erro(client, db_session, token_acesso):
    cargo = criar_cargo(db_session, {"gerenciar_processos": True})
    usuario = criar_funcionario(db_session, cargo, "del.erro@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.delete("/processos/1/documentos/99999", headers=auth_header(token))
    assert response.status_code == 404
    assert "Documento não encontrado" in response.json()["detail"]


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.remover_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_controller_deletar_documento_controller_sucesso(
    mock_url, mock_remover, mock_salvar, client, db_session, token_acesso, cliente_processo
):
    cargo = criar_cargo(db_session, {"gerenciar_processos": True, "visualizar_processos": True})
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
def test_controller_obter_resumo_processos_controller_parametrizado(
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
        "gerenciar_equipe": eh_admin,
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


def test_controller_obter_resumo_processos_sem_autenticacao_e_sem_permissao(
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
def test_controller_atualizar_processo_campo_obrigatorio_nulo_retorna_422(
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


ROTA = "/processos/exportar"


@pytest.fixture
def auth(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture
def processos(db_session):
    cliente = Cliente(nome="Maria da Silva", email="maria@teste.com", telefone="61999999999")
    db_session.add(cliente)
    db_session.flush()
    itens = [
        Processo(
            descricao="Descrição",
            data_inicio=datetime(2026, 1, 1),
            funcionario_id=1,
            cnj=f"000000000000000000{indice:02d}",
            titulo=titulo,
            tribunal="TJDFT",
            area="Civil",
            status=status,
            data_prazo=datetime(2026, 10, 30),
            cliente_id=cliente.cliente_id,
        )
        for indice, (titulo, status) in enumerate(
            [
                ("Alfa", StatusProcesso.ATIVO),
                ("Beta", StatusProcesso.ARQUIVADO),
                ("Gama", StatusProcesso.ATIVO),
            ]
        )
    ]
    db_session.add_all(itens)
    db_session.commit()
    return itens


def _planilha(response):
    return load_workbook(io.BytesIO(response.content)).active


@pytest.mark.parametrize(
    ("formato", "media_type", "inicio"),
    [
        ("csv", "text/csv", b"\xef\xbb\xbf"),
        ("xlsx", "application/vnd.openxmlformats", b"PK"),
        ("pdf", "application/pdf", b"%PDF"),
    ],
)
def test_exportacao_exportar_cada_formato(client, auth, processos, formato, media_type, inicio):
    response = client.get(ROTA, params={"formato": formato}, headers=auth)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
    assert response.content.startswith(inicio)
    assert "processos_" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith(f'.{formato}"')


def test_exportacao_exportar_aplica_filtros_e_ignora_paginacao(client, auth, processos):
    todos = client.get(ROTA, params={"formato": "xlsx", "page_size": 1}, headers=auth)
    ativos = client.get(ROTA, params={"formato": "xlsx", "status": "Ativo"}, headers=auth)

    assert _planilha(todos).max_row == 4
    planilha = _planilha(ativos)
    assert [linha[1].value for linha in planilha.iter_rows(min_row=2)] == ["Gama", "Alfa"]


def test_exportacao_exportar_inclui_nome_do_cliente(client, auth, processos):
    planilha = _planilha(client.get(ROTA, params={"formato": "xlsx"}, headers=auth))

    cabecalho = [c.value for c in planilha[1]]
    assert planilha.cell(2, cabecalho.index("Cliente") + 1).value == "Maria da Silva"
    assert "cliente_id" not in cabecalho


def test_exportacao_exportar_sem_resultados_gera_somente_cabecalho(client, auth, processos):
    response = client.get(ROTA, params={"formato": "xlsx", "tribunal": "inexistente"}, headers=auth)

    assert response.status_code == 200
    assert _planilha(response).max_row == 1


def test_exportacao_exportar_exige_formato_valido(client, auth):
    assert client.get(ROTA, headers=auth).status_code == 422
    assert client.get(ROTA, params={"formato": "docx"}, headers=auth).status_code == 422


def test_exportacao_exportar_respeita_limite_de_linhas(client, auth, processos, monkeypatch):
    monkeypatch.setattr("app.processo.service.LIMITE_LINHAS", 2)

    response = client.get(ROTA, params={"formato": "csv"}, headers=auth)

    assert response.status_code == 422
    assert "refine os filtros" in response.json()["detail"]


def test_exportacao_exportar_exige_visualizar_processos(
    client, token_acesso, funcionario_sem_permissao
):
    usuario = funcionario_sem_permissao
    token = token_acesso(usuario.funcionario_id, usuario.email)

    response = client.get(
        ROTA, params={"formato": "csv"}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_exportacao_exportar_exige_autenticacao(client):
    assert client.get(ROTA, params={"formato": "csv"}).status_code == 401


@pytest.fixture
def dados_base(db_session: Session):
    cargo = Cargo(
        nome_cargo="Advogado",
        descricao="Cargo de teste",
        permissao={},
    )

    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)

    funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Funcionário Teste",
        email="funcionario@teste.com",
        status=StatusFuncionario.ATIVO,
        cargo_id=cargo.cargo_id,
    )

    cliente = Cliente(
        nome="Cliente Teste",
        telefone="61999999999",
        email="cliente@teste.com",
        area_interesse="Civil",
        ultima_interacao=datetime(2026, 1, 1),
        responsavel_id=None,
        etapa_id=1,
    )

    db_session.add_all([funcionario, cliente])
    db_session.commit()

    db_session.refresh(funcionario)
    db_session.refresh(cliente)

    return {
        "funcionario": funcionario,
        "cliente": cliente,
    }


@pytest.fixture
def processo(dados_base, db_session):
    processo = Processo(
        cnj="11111111111111111111",
        titulo="Processo Teste",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        data_inicio=datetime(2026, 1, 1),
        data_realizado=None,
        data_prazo=datetime(2026, 12, 31),
        cliente_id=dados_base["cliente"].cliente_id,
        funcionario_id=dados_base["funcionario"].funcionario_id,
    )

    db_session.add(processo)
    db_session.commit()
    db_session.refresh(processo)

    return processo


def buscar_com_filtro(repository, **filtros):
    return repository.buscar_paginado_por_filtros(
        page=1,
        page_size=10,
        **filtros,
    )


def test_repository_buscar_todos(db_session, processo):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_todos()

    assert len(resultado) == 1
    assert resultado[0].processo_id == processo.processo_id


def test_repository_buscar_por_id_encontra_processo(db_session, processo):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_por_id(processo.processo_id)

    assert resultado is not None
    assert resultado.processo_id == processo.processo_id


def test_repository_buscar_por_filtros_busca_textual_e_datas_prazo(db_session, processo):
    repository = ProcessoRepository(db_session)

    itens_busca, total_busca = repository.buscar_paginado_por_filtros(
        page=1,
        page_size=10,
        busca=processo.titulo,
    )
    assert total_busca == 1
    assert len(itens_busca) == 1

    prazo_data = processo.data_prazo.date()
    itens_prazo, total_prazo = repository.buscar_paginado_por_filtros(
        page=1,
        page_size=10,
        prazo_inicio=prazo_data,
        prazo_fim=prazo_data,
    )
    assert total_prazo == 1
    assert len(itens_prazo) == 1


def test_repository_buscar_por_id_nao_encontra_processo(db_session):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_por_id(999999)

    assert resultado is None


def test_repository_buscar_por_cnj_encontra_processo(db_session, processo):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_por_cnj(processo.cnj)

    assert resultado is not None
    assert resultado.processo_id == processo.processo_id


def test_repository_buscar_por_cnj_nao_encontra_processo(db_session):
    repository = ProcessoRepository(db_session)

    resultado = repository.buscar_por_cnj("99999999999999999999")

    assert resultado is None


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("cnj", "1111111111"),
        ("titulo", "Processo"),
        ("descricao", "Descrição"),
        ("tribunal", "TJSP"),
        ("area", "Civil"),
    ],
)
def test_repository_buscar_por_filtros_textuais(
    db_session,
    processo,
    campo,
    valor,
):
    repository = ProcessoRepository(db_session)

    itens, total = buscar_com_filtro(repository, **{campo: valor})

    assert total == 1
    assert len(itens) == 1
    assert itens[0].processo_id == processo.processo_id


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("processo_id", "processo_id"),
        ("cliente_id", "cliente_id"),
        ("funcionario_id", "funcionario_id"),
    ],
)
def test_repository_buscar_por_filtros_ids(
    db_session,
    processo,
    campo,
    valor,
):
    repository = ProcessoRepository(db_session)

    valores = {
        "processo_id": processo.processo_id,
        "cliente_id": processo.cliente_id,
        "funcionario_id": processo.funcionario_id,
    }

    itens, total = buscar_com_filtro(
        repository,
        **{campo: valores[valor]},
    )

    assert total == 1
    assert len(itens) == 1
    assert itens[0].processo_id == processo.processo_id


@pytest.mark.parametrize(
    "status",
    [
        StatusProcesso.EM_ANALISE,
        StatusProcesso.ATIVO,
        StatusProcesso.CONCLUIDO,
        StatusProcesso.ARQUIVADO,
    ],
)
def test_repository_buscar_por_status(db_session, dados_base, status):
    processo = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        cnj=f"{list(StatusProcesso).index(status) + 2:020d}",
        titulo="Processo",
        status=status,
        tribunal="TJSP",
        area="Civil",
        cliente_id=dados_base["cliente"].cliente_id,
        funcionario_id=dados_base["funcionario"].funcionario_id,
    )

    db_session.add(processo)
    db_session.commit()

    repository = ProcessoRepository(db_session)

    itens, total = buscar_com_filtro(
        repository,
        status=status,
    )

    assert total == 1
    assert len(itens) == 1
    assert itens[0].status == status


def test_repository_buscar_por_filtros_sem_resultado(db_session):
    repository = ProcessoRepository(db_session)

    itens, total = buscar_com_filtro(
        repository,
        titulo="Não Existe",
    )

    assert itens == []
    assert total == 0


def test_repository_buscar_por_filtros_paginado(db_session, dados_base):
    repository = ProcessoRepository(db_session)

    processos = []

    for i in range(3):
        processo = Processo(
            descricao="Descrição",
            data_inicio=datetime(2026, 1, 1),
            data_prazo=datetime(2026, 12, 31),
            cnj=f"{i + 1:020d}",
            titulo=f"Processo {i + 1}",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=dados_base["cliente"].cliente_id,
            funcionario_id=dados_base["funcionario"].funcionario_id,
        )
        db_session.add(processo)
        processos.append(processo)

    db_session.commit()

    itens, total = repository.buscar_paginado_por_filtros(
        page=1,
        page_size=2,
    )

    assert total == 3
    assert len(itens) == 2


def test_repository_buscar_por_filtros_pagina_alem_do_fim(db_session, processo):
    repository = ProcessoRepository(db_session)

    itens, total = repository.buscar_paginado_por_filtros(
        page=100,
        page_size=10,
    )

    assert total == 1
    assert itens == []


def test_repository_criar(db_session, dados_base):
    repository = ProcessoRepository(db_session)

    processo = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        cnj="22222222222222222222",
        titulo="Novo Processo",
        status=StatusProcesso.EM_ANALISE,
        tribunal="TRF1",
        area="Tributária",
        cliente_id=dados_base["cliente"].cliente_id,
        funcionario_id=dados_base["funcionario"].funcionario_id,
    )

    resultado = repository.criar(processo)

    assert resultado.processo_id is not None
    assert resultado.cnj == "22222222222222222222"


def test_repository_atualizar(db_session, processo):
    repository = ProcessoRepository(db_session)

    processo.titulo = "Título Atualizado"

    resultado = repository.atualizar(processo)

    assert resultado.titulo == "Título Atualizado"


def test_repository_deletar(db_session, processo):
    repository = ProcessoRepository(db_session)

    processo_id = processo.processo_id

    repository.deletar(processo)

    resultado = repository.buscar_por_id(processo_id)

    assert resultado is None


@pytest.mark.parametrize(
    "status,data_realizado,data_inicio,func_vinculo,dias_filtro,func_filtro,espera_critico",
    [
        (StatusProcesso.ATIVO, None, datetime.now(UTC) - timedelta(days=40), True, 30, None, True),
        (
            StatusProcesso.ATIVO,
            datetime.now(UTC) - timedelta(days=5),
            datetime.now(UTC) - timedelta(days=40),
            True,
            30,
            None,
            False,
        ),
        (
            StatusProcesso.ATIVO,
            datetime.now(UTC) - timedelta(days=45),
            datetime.now(UTC) - timedelta(days=100),
            True,
            30,
            None,
            True,
        ),
        (
            StatusProcesso.CONCLUIDO,
            None,
            datetime.now(UTC) - timedelta(days=50),
            True,
            30,
            None,
            False,
        ),
        (
            StatusProcesso.ARQUIVADO,
            None,
            datetime.now(UTC) - timedelta(days=50),
            True,
            30,
            None,
            False,
        ),
        (StatusProcesso.ATIVO, None, datetime.now(UTC) - timedelta(days=40), False, 30, 999, False),
        (StatusProcesso.ATIVO, None, datetime.now(UTC) - timedelta(days=40), True, 30, True, True),
        (StatusProcesso.ATIVO, None, datetime.now(UTC) - timedelta(days=15), True, 10, None, True),
    ],
)
def test_repository_buscar_por_filtros_atividade_e_status_excluidos(
    db_session,
    dados_base,
    status,
    data_realizado,
    data_inicio,
    func_vinculo,
    dias_filtro,
    func_filtro,
    espera_critico,
):
    repository = ProcessoRepository(db_session)
    funcionario = dados_base["funcionario"]
    cliente = dados_base["cliente"]

    if func_vinculo:
        funcionario_id = funcionario.funcionario_id
    else:
        outro = Funcionario(
            atuacao_id=1,
            foto_perfil=1,
            nome="Outro Advogado",
            email="outro.advogado@test.com",
            cargo_id=funcionario.cargo_id,
        )
        db_session.add(outro)
        db_session.commit()
        funcionario_id = outro.funcionario_id

    proc = Processo(
        descricao="Descrição",
        data_prazo=datetime(2026, 12, 31),
        cnj="99999999999999999999",
        titulo="Processo Teste Crítico",
        status=status,
        tribunal="TJDFT",
        area="Trabalhista",
        cliente_id=cliente.cliente_id,
        funcionario_id=funcionario_id,
        data_realizado=data_realizado,
        data_inicio=data_inicio,
    )
    repository.criar(proc)

    filtro_func = funcionario.funcionario_id if func_filtro is True else func_filtro

    criticos = repository.buscar_por_filtros(
        status_excluidos=[StatusProcesso.CONCLUIDO, StatusProcesso.ARQUIVADO],
        ultima_atividade_ate=datetime.now(UTC) - timedelta(days=dias_filtro),
        funcionario_id=filtro_func,
    )

    if espera_critico:
        assert any(p.processo_id == proc.processo_id for p in criticos)
    else:
        assert not any(p.processo_id == proc.processo_id for p in criticos)


def test_repository_documento_repository_crud(db_session: Session, dados_base: dict):
    repository = ProcessoRepository(db_session)
    cliente = dados_base["cliente"]
    funcionario = dados_base["funcionario"]

    proc = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        cnj="88888888888888888888",
        titulo="Processo com Documento",
        status=StatusProcesso.ATIVO,
        tribunal="TJDFT",
        area="Civil",
        cliente_id=cliente.cliente_id,
        funcionario_id=funcionario.funcionario_id,
    )
    repository.criar(proc)

    docs = repository.listar_documentos(proc.processo_id)
    assert docs == []

    # Adicionar documento
    doc = Arquivo(
        nome_arquivo="peticao.pdf",
        bucket_link=f"processos/{proc.processo_id}/peticao.pdf",
        origem="manual",
        tamanho_bytes=2048,
        tipo_mime="application/pdf",
        funcionario_id=funcionario.funcionario_id,
    )
    doc_salvo = repository.adicionar_documento(proc.processo_id, doc)
    assert doc_salvo.arquivo_id is not None
    assert doc_salvo.nome_arquivo == "peticao.pdf"
    assert doc_salvo.origem == "manual"

    doc_encontrado = repository.buscar_documento(proc.processo_id, doc_salvo.arquivo_id)
    assert doc_encontrado is not None
    assert doc_encontrado.bucket_link == doc.bucket_link

    assert repository.buscar_documento(proc.processo_id, 999999) is None
    assert repository.buscar_documento(proc.processo_id + 1, doc_salvo.arquivo_id) is None

    docs_listados = repository.listar_documentos(proc.processo_id)
    assert len(docs_listados) == 1
    assert docs_listados[0].arquivo_id == doc_salvo.arquivo_id

    repository.deletar_documento(proc.processo_id, doc_salvo)
    assert repository.buscar_documento(proc.processo_id, doc_salvo.arquivo_id) is None
    assert repository.listar_documentos(proc.processo_id) == []
    assert db_session.query(Arquivo).count() == 0


def test_repository_deletar_processo_remove_arquivos_vinculados(
    db_session: Session, dados_base: dict
):
    repository = ProcessoRepository(db_session)
    proc = Processo(
        cnj="77777777777777777777",
        titulo="Processo com Arquivos",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJDFT",
        area="Civil",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        cliente_id=dados_base["cliente"].cliente_id,
        funcionario_id=dados_base["funcionario"].funcionario_id,
    )
    repository.criar(proc)
    for nome in ("a.pdf", "b.pdf"):
        repository.adicionar_documento(
            proc.processo_id,
            Arquivo(
                nome_arquivo=nome,
                tipo_mime="application/pdf",
                tamanho_bytes=1,
                bucket_link=f"processos/{nome}",
            ),
        )

    repository.deletar(proc)

    assert db_session.query(Arquivo).count() == 0
    assert db_session.query(ProcessoArquivo).count() == 0


@pytest.mark.parametrize(
    "filtrar_por_funcionario,esperado",
    [
        (
            False,
            {
                StatusProcesso.ATIVO: 2,
                StatusProcesso.EM_ANALISE: 1,
                StatusProcesso.CONCLUIDO: 1,
                StatusProcesso.ARQUIVADO: 1,
            },
        ),
        (
            True,
            {
                StatusProcesso.ATIVO: 1,
                StatusProcesso.EM_ANALISE: 1,
                StatusProcesso.CONCLUIDO: 1,
            },
        ),
    ],
)
def test_repository_contar_por_status_parametrizado(
    db_session,
    dados_base,
    filtrar_por_funcionario,
    esperado,
):
    repository = ProcessoRepository(db_session)
    funcionario = dados_base["funcionario"]
    cliente = dados_base["cliente"]

    outro_funcionario = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Outro Advogado",
        email="outro.adv@teste.com",
        status=StatusFuncionario.ATIVO,
        cargo_id=funcionario.cargo_id,
    )
    db_session.add(outro_funcionario)
    db_session.commit()
    db_session.refresh(outro_funcionario)

    processos_seed = [
        ("10000000000000000001", StatusProcesso.ATIVO, funcionario.funcionario_id),
        ("10000000000000000002", StatusProcesso.ATIVO, outro_funcionario.funcionario_id),
        ("10000000000000000003", StatusProcesso.EM_ANALISE, funcionario.funcionario_id),
        ("10000000000000000004", StatusProcesso.CONCLUIDO, funcionario.funcionario_id),
        ("10000000000000000005", StatusProcesso.ARQUIVADO, outro_funcionario.funcionario_id),
    ]
    for cnj, status_proc, func_id in processos_seed:
        repository.criar(
            Processo(
                descricao="Descrição",
                data_inicio=datetime(2026, 1, 1),
                data_prazo=datetime(2026, 12, 31),
                cnj=cnj,
                titulo=f"Proc {cnj}",
                status=status_proc,
                tribunal="TJDFT",
                area="Civil",
                cliente_id=cliente.cliente_id,
                funcionario_id=func_id,
            )
        )

    filtro_id = funcionario.funcionario_id if filtrar_por_funcionario else None
    resultado = repository.contar_por_status(funcionario_id=filtro_id)

    assert resultado == esperado


@pytest.mark.parametrize(
    "dias_offset_inicio,dias_offset_fim,incluir_excluidos,esperado",
    [
        (-10, -1, True, 1),
        (0, 7, True, 2),
        (0, 7, False, 3),
        (30, 60, True, 0),
    ],
)
def test_repository_contar_por_filtros_prazos_parametrizado(
    db_session,
    dados_base,
    dias_offset_inicio,
    dias_offset_fim,
    incluir_excluidos,
    esperado,
):
    repository = ProcessoRepository(db_session)
    funcionario = dados_base["funcionario"]
    cliente = dados_base["cliente"]
    hoje = datetime.now(UTC).date()

    processos_seed = [
        (
            "20000000000000000001",
            StatusProcesso.ATIVO,
            datetime.combine(hoje - timedelta(days=3), datetime.min.time()),
        ),
        (
            "20000000000000000002",
            StatusProcesso.ATIVO,
            datetime.combine(hoje + timedelta(days=2), datetime.min.time()),
        ),
        (
            "20000000000000000003",
            StatusProcesso.EM_ANALISE,
            datetime.combine(hoje + timedelta(days=5), datetime.min.time()),
        ),
        (
            "20000000000000000004",
            StatusProcesso.CONCLUIDO,
            datetime.combine(hoje + timedelta(days=2), datetime.min.time()),
        ),
    ]
    for cnj, status_proc, data_prazo in processos_seed:
        repository.criar(
            Processo(
                descricao="Descrição",
                data_inicio=datetime(2026, 1, 1),
                cnj=cnj,
                titulo=f"Proc Prazo {cnj}",
                status=status_proc,
                tribunal="TJDFT",
                area="Civil",
                cliente_id=cliente.cliente_id,
                funcionario_id=funcionario.funcionario_id,
                data_prazo=data_prazo,
            )
        )

    excluidos = [StatusProcesso.CONCLUIDO, StatusProcesso.ARQUIVADO] if incluir_excluidos else None
    total = repository.contar_por_filtros(
        status_excluidos=excluidos,
        funcionario_id=funcionario.funcionario_id,
        prazo_inicio=hoje + timedelta(days=dias_offset_inicio),
        prazo_fim=hoje + timedelta(days=dias_offset_fim),
    )

    assert total == esperado


def test_repository_buscar_por_filtros_com_busca_textual(db_session, processo):
    repository = ProcessoRepository(db_session)
    encontrados = repository.buscar_por_filtros(busca="Cliente Teste")
    assert len(encontrados) == 1
    assert encontrados[0].processo_id == processo.processo_id


def test_repository_registrar_listar_movimentacoes_e_deletar_processo(
    db_session: Session, processo: Processo
):
    repository = ProcessoRepository(db_session)

    movimentacao_criacao = repository.registrar_movimentacao(
        ProcessoMovimentacao(
            processo_id=processo.processo_id,
            funcionario_id=processo.funcionario_id,
            tipo_movimentacao=TipoMovimentacaoProcesso.CRIACAO_PROCESSO,
            descricao="Processo criado.",
        )
    )
    movimentacao_upload = repository.registrar_movimentacao(
        ProcessoMovimentacao(
            processo_id=processo.processo_id,
            funcionario_id=None,
            tipo_movimentacao=TipoMovimentacaoProcesso.UPLOAD_ARQUIVO,
            descricao="Arquivo adicionado.",
        )
    )

    movimentacoes = repository.listar_movimentacoes(processo.processo_id)

    assert movimentacao_criacao.movimentacao_id is not None
    assert movimentacao_upload.movimentacao_id is not None
    assert [mov.movimentacao_id for mov in movimentacoes] == [
        movimentacao_upload.movimentacao_id,
        movimentacao_criacao.movimentacao_id,
    ]

    repository.deletar(processo)

    assert db_session.query(ProcessoMovimentacao).count() == 0


def processo_valido() -> dict:
    return {
        "cnj": "11111111111111111111",
        "titulo": "Processo Teste",
        "descricao": "Descrição do processo",
        "status": StatusProcesso.ATIVO,
        "tribunal": "TJSP",
        "area": "Civil",
        "data_inicio": "2026-01-01T00:00:00",
        "data_realizado": "2026-01-10T00:00:00",
        "data_prazo": "2026-12-31T00:00:00",
        "cliente_id": 1,
        "funcionario_id": 1,
    }


def test_schema_processo_create_valido():
    processo = ProcessoCreate(**processo_valido())

    assert processo.cnj == "11111111111111111111"
    assert processo.titulo == "Processo Teste"
    assert processo.status == StatusProcesso.ATIVO
    assert processo.cliente_id == 1
    assert processo.funcionario_id == 1


def test_schema_status_padrao_e_em_analise():
    dados = processo_valido()
    dados.pop("status")

    processo = ProcessoCreate(**dados)

    assert processo.status == StatusProcesso.EM_ANALISE


@pytest.mark.parametrize(
    "status",
    [
        StatusProcesso.EM_ANALISE,
        StatusProcesso.ATIVO,
        StatusProcesso.CONCLUIDO,
        StatusProcesso.ARQUIVADO,
    ],
)
def test_schema_status_validos(status):
    dados = processo_valido()
    dados["status"] = status

    processo = ProcessoCreate(**dados)

    assert processo.status == status


def test_schema_status_invalido():
    dados = processo_valido()
    dados["status"] = "Pendente"

    with pytest.raises(ValidationError):
        ProcessoCreate(**dados)


@pytest.mark.parametrize(
    ("campo", "tamanho"),
    [
        ("cnj", 26),
        ("titulo", 101),
        ("descricao", 256),
        ("tribunal", 101),
        ("area", 101),
    ],
)
def test_schema_limite_maximo_dos_campos(campo, tamanho):
    dados = processo_valido()
    dados[campo] = "a" * tamanho

    with pytest.raises(ValidationError):
        ProcessoCreate(**dados)


@pytest.mark.parametrize(
    "campo",
    ["descricao", "data_inicio", "data_prazo", "funcionario_id"],
)
def test_schema_campos_obrigatorios_nao_aceitam_nulo_nem_ausencia(campo):
    dados = processo_valido()
    dados[campo] = None
    with pytest.raises(ValidationError):
        ProcessoCreate(**dados)

    dados.pop(campo)
    with pytest.raises(ValidationError):
        ProcessoCreate(**dados)


def test_schema_data_realizado_pode_ser_nula():
    dados = processo_valido()
    dados["data_realizado"] = None

    assert ProcessoCreate(**dados).data_realizado is None


def test_schema_cliente_id_e_obrigatorio():
    dados = processo_valido()
    dados.pop("cliente_id")

    with pytest.raises(ValidationError):
        ProcessoCreate(**dados)


def test_schema_processo_update_aceita_atualizacao_parcial():
    processo = ProcessoUpdate(
        status=StatusProcesso.CONCLUIDO,
    )

    assert processo.status == StatusProcesso.CONCLUIDO
    assert processo.titulo is None
    assert processo.area is None


def test_schema_processo_update_aceita_funcionario():
    processo = ProcessoUpdate(
        funcionario_id=10,
    )

    assert processo.funcionario_id == 10


def test_schema_processo_filter():
    filtros = ProcessoFilter(
        processo_id=10,
        cnj="123",
        titulo="Teste",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=20,
        funcionario_id=30,
    )

    assert filtros.processo_id == 10
    assert filtros.cnj == "123"
    assert filtros.titulo == "Teste"
    assert filtros.descricao == "Descrição"
    assert filtros.status == StatusProcesso.ATIVO
    assert filtros.tribunal == "TJSP"
    assert filtros.area == "Civil"
    assert filtros.cliente_id == 20
    assert filtros.funcionario_id == 30


def test_schema_processo_response():
    dados = processo_valido()
    dados["processo_id"] = 1

    response = ProcessoResponse(**dados)

    assert response.processo_id == 1
    assert response.funcionario_id == 1


def test_schema_documento_processo_response():
    agora = "2026-01-01T12:00:00"
    dados = {
        "documento_id": 10,
        "processo_id": 1,
        "nome_original": "peticao.pdf",
        "chave_minio": "processos/1/abc.pdf",
        "origem": "manual",
        "tamanho_bytes": 1024,
        "entrada_tipo": "application/pdf",
        "data_upload": agora,
        "funcionario_id": 2,
        "url": "http://minio/peticao.pdf",
    }
    response = DocumentoProcessoResponse(**dados)
    assert response.documento_id == 10
    assert response.processo_id == 1
    assert response.nome_original == "peticao.pdf"
    assert response.chave_minio == "processos/1/abc.pdf"
    assert response.origem == "manual"
    assert response.entrada_tipo == "application/pdf"
    assert response.url == "http://minio/peticao.pdf"


def test_schema_documento_url_response():
    response = DocumentoUrlResponse(
        documento_id=10,
        url="http://minio/download",
    )
    assert response.documento_id == 10
    assert response.url == "http://minio/download"
    assert response.expira_em_segundos == 1800


def test_schema_processo_resumo_response_padrao_e_customizado():
    from app.processo.schema import ProcessoResumoResponse

    padrao = ProcessoResumoResponse()
    assert padrao.total == 0
    assert padrao.em_andamento == 0
    assert padrao.em_analise == 0
    assert padrao.finalizados == 0
    assert padrao.proximos_do_prazo == 0
    assert padrao.atrasados == 0

    custom = ProcessoResumoResponse(
        total=10,
        em_andamento=4,
        em_analise=2,
        finalizados=4,
        proximos_do_prazo=2,
        atrasados=1,
    )
    assert custom.total == 10
    assert custom.em_andamento == 4
    assert custom.em_analise == 2
    assert custom.finalizados == 4
    assert custom.proximos_do_prazo == 2
    assert custom.atrasados == 1


def criar_service():
    db = MagicMock()
    service = ProcessoService(db)
    service.repository = MagicMock()
    return service


def dados_processo_create() -> ProcessoCreate:
    return ProcessoCreate(
        cnj="11111111111111111111",
        titulo="Processo Teste",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        cliente_id=1,
        funcionario_id=2,
    )


def test_service_buscar_todos():
    service = criar_service()

    processos = [MagicMock(spec=Processo)]
    service.repository.buscar_todos.return_value = processos

    resultado = service.buscar_todos()

    assert resultado == processos
    service.repository.buscar_todos.assert_called_once()


def test_service_buscar_processos():
    service = criar_service()

    filtros = ProcessoFilter(
        processo_id=None,
        cnj=None,
        titulo="Teste",
        descricao=None,
        status=StatusProcesso.ATIVO,
        tribunal=None,
        area=None,
        cliente_id=1,
        funcionario_id=2,
        busca=None,
        prazo_inicio=None,
        prazo_fim=None,
        page=1,
        page_size=10,
    )

    processo = Processo(
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        processo_id=1,
        cnj="11111111111111111111",
        titulo="Processo Teste",
        descricao="Descrição",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=1,
        funcionario_id=2,
    )

    service.repository.buscar_paginado_por_filtros.return_value = ([processo], 1)

    resultado = service.buscar_processos(filtros)

    assert resultado.total == 1
    assert resultado.page == 1
    assert resultado.page_size == 10
    assert resultado.total_pages == 1
    assert len(resultado.itens) == 1
    assert resultado.itens[0].processo_id == processo.processo_id

    service.repository.buscar_paginado_por_filtros.assert_called_once_with(
        page=1,
        page_size=10,
        processo_id=None,
        cnj=None,
        titulo="Teste",
        descricao=None,
        status=StatusProcesso.ATIVO,
        tribunal=None,
        area=None,
        cliente_id=1,
        funcionario_id=2,
        busca=None,
        prazo_inicio=None,
        prazo_fim=None,
    )


def test_service_buscar_processos_com_paginacao():
    service = criar_service()

    filtros = ProcessoFilter(
        processo_id=None,
        cnj=None,
        titulo=None,
        descricao=None,
        status=None,
        tribunal=None,
        area=None,
        cliente_id=None,
        funcionario_id=None,
        busca=None,
        prazo_inicio=None,
        prazo_fim=None,
        page=2,
        page_size=5,
    )

    processos = [
        Processo(
            descricao="Descrição",
            data_inicio=datetime(2026, 1, 1),
            data_prazo=datetime(2026, 12, 31),
            funcionario_id=1,
            processo_id=6,
            cnj="66666666666666666666",
            titulo="Processo 6",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=1,
        ),
        Processo(
            descricao="Descrição",
            data_inicio=datetime(2026, 1, 1),
            data_prazo=datetime(2026, 12, 31),
            funcionario_id=1,
            processo_id=7,
            cnj="77777777777777777777",
            titulo="Processo 7",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=1,
        ),
    ]

    service.repository.buscar_paginado_por_filtros.return_value = (processos, 12)

    resultado = service.buscar_processos(filtros)

    assert resultado.total == 12
    assert resultado.page == 2
    assert resultado.page_size == 5
    assert resultado.total_pages == 3
    assert len(resultado.itens) == 2


def test_service_buscar_processos_sem_resultado():
    service = criar_service()

    filtros = ProcessoFilter(
        processo_id=None,
        cnj=None,
        titulo="Não Existe",
        descricao=None,
        status=None,
        tribunal=None,
        area=None,
        cliente_id=None,
        funcionario_id=None,
        busca=None,
        prazo_inicio=None,
        prazo_fim=None,
        page=1,
        page_size=10,
    )

    service.repository.buscar_paginado_por_filtros.return_value = ([], 0)

    resultado = service.buscar_processos(filtros)

    assert resultado.itens == []
    assert resultado.total == 0
    assert resultado.page == 1
    assert resultado.page_size == 10
    assert resultado.total_pages == 1


def test_service_criar_processo():
    service = criar_service()

    dados = dados_processo_create()

    service.repository.buscar_por_cnj.return_value = None

    processo_criado = MagicMock(spec=Processo)
    service.repository.criar.return_value = processo_criado

    resultado = service.criar_processo(dados)

    assert resultado == processo_criado

    service.repository.buscar_por_cnj.assert_called_once_with(dados.cnj)
    service.repository.criar.assert_called_once()


def test_service_criar_processo_com_cnj_existente():
    service = criar_service()

    dados = dados_processo_create()

    processo_existente = MagicMock(spec=Processo)

    service.repository.buscar_por_cnj.return_value = processo_existente

    with pytest.raises(ValueError, match="Processo já cadastrado"):
        service.criar_processo(dados)

    service.repository.criar.assert_not_called()


def test_service_atualizar_processo():
    service = criar_service()

    processo = MagicMock(spec=Processo)
    processo.processo_id = 1

    dados = ProcessoUpdate(
        titulo="Novo título",
        status=StatusProcesso.CONCLUIDO,
        funcionario_id=10,
    )

    service.repository.buscar_por_id.return_value = processo
    service.repository.buscar_por_cnj.return_value = None
    service.repository.atualizar.return_value = processo

    resultado = service.atualizar_processo(1, dados)

    assert resultado == processo
    assert processo.titulo == "Novo título"
    assert processo.status == StatusProcesso.CONCLUIDO
    assert processo.funcionario_id == 10

    service.repository.atualizar.assert_called_once_with(processo)


def test_service_atualizar_processo_sem_mudar_status_nao_registra_movimentacao():
    service = criar_service()

    processo = MagicMock(spec=Processo)
    processo.processo_id = 1
    processo.status = StatusProcesso.ATIVO

    dados = ProcessoUpdate(titulo="Apenas correção de título")

    service.repository.buscar_por_id.return_value = processo
    service.repository.atualizar.return_value = processo

    service.atualizar_processo(1, dados)

    service.repository.atualizar.assert_called_once_with(processo)
    service.repository.registrar_movimentacao.assert_not_called()


@pytest.mark.parametrize("campo", ["descricao", "data_inicio", "data_prazo", "funcionario_id"])
def test_service_atualizar_processo_campo_obrigatorio_nulo_lanca_erro(campo):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)

    with pytest.raises(ValueError, match=f"O campo '{campo}' não pode ser nulo"):
        service.atualizar_processo(1, ProcessoUpdate(**{campo: None}))

    service.repository.atualizar.assert_not_called()


def test_service_atualizar_processo_inexistente():
    service = criar_service()

    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.atualizar_processo(
            999,
            ProcessoUpdate(titulo="Teste"),
        )

    service.repository.atualizar.assert_not_called()


def test_service_atualizar_processo_com_cnj_duplicado():
    service = criar_service()

    processo_atual = MagicMock(spec=Processo)
    processo_atual.processo_id = 1

    outro_processo = MagicMock(spec=Processo)
    outro_processo.processo_id = 2

    service.repository.buscar_por_id.return_value = processo_atual
    service.repository.buscar_por_cnj.return_value = outro_processo

    with pytest.raises(ValueError, match="CNJ já cadastrado"):
        service.atualizar_processo(
            1,
            ProcessoUpdate(
                cnj="22222222222222222222",
            ),
        )

    service.repository.atualizar.assert_not_called()


def test_service_atualizar_processo_com_mesmo_cnj():
    service = criar_service()

    processo = MagicMock(spec=Processo)
    processo.processo_id = 1

    service.repository.buscar_por_id.return_value = processo
    service.repository.buscar_por_cnj.return_value = processo
    service.repository.atualizar.return_value = processo

    resultado = service.atualizar_processo(
        1,
        ProcessoUpdate(
            cnj="11111111111111111111",
        ),
    )

    assert resultado == processo
    service.repository.atualizar.assert_called_once_with(processo)


@patch("app.processo.service.remover_arquivo")
def test_service_deletar_processo(mock_remover):
    service = criar_service()

    processo = MagicMock(spec=Processo)
    doc = MagicMock(bucket_link="processos/1/doc.pdf")

    service.repository.buscar_por_id.return_value = processo
    service.repository.listar_documentos.return_value = [doc]

    service.deletar_processo(1)

    mock_remover.assert_called_once_with("processos/1/doc.pdf", bucket="privado")
    service.repository.deletar.assert_called_once_with(processo)


def test_service_deletar_processo_inexistente():
    service = criar_service()

    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.deletar_processo(999)

    service.repository.deletar.assert_not_called()


@pytest.mark.parametrize(
    "dias,func_id",
    [
        (30, None),
        (15, 1),
        (60, 2),
        (0, None),
    ],
)
def test_service_buscar_processos_criticos_parametrizado(dias, func_id):
    funcionario_do_processo = func_id or 3
    service = criar_service()
    processos = [
        Processo(
            descricao="Descrição",
            data_inicio=datetime(2026, 1, 1),
            data_prazo=datetime(2026, 12, 31),
            processo_id=1,
            cnj="11111111111111111111",
            titulo="Proc Crítico",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=1,
            funcionario_id=funcionario_do_processo,
        )
    ]
    service.repository.buscar_por_filtros.return_value = processos

    antes = datetime.now(UTC) - timedelta(days=dias)
    resultado = service.buscar_processos_criticos(
        dias_sem_movimentacao=dias,
        funcionario_id=func_id,
    )
    depois = datetime.now(UTC) - timedelta(days=dias)

    assert len(resultado) == 1
    assert resultado[0].processo_id == 1
    assert resultado[0].cnj == "11111111111111111111"
    service.repository.buscar_por_filtros.assert_called_once()
    kwargs = service.repository.buscar_por_filtros.call_args.kwargs
    assert kwargs["status_excluidos"] == [StatusProcesso.CONCLUIDO, StatusProcesso.ARQUIVADO]
    assert kwargs["funcionario_id"] == func_id
    assert antes <= kwargs["ultima_atividade_ate"] <= depois


def test_service_adicionar_documento_processo_inexistente():
    service = criar_service()
    service.repository.buscar_por_id.return_value = None

    file_mock = MagicMock(spec=UploadFile)
    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.adicionar_documento(999, file_mock)


def test_service_adicionar_documento_arquivo_vazio():
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)

    file_mock = UploadFile(filename="vazio.pdf", file=io.BytesIO(b""))
    with pytest.raises(ValueError, match="O arquivo enviado está vazio."):
        service.adicionar_documento(1, file_mock)


def test_service_adicionar_documento_tamanho_excedido():
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)

    conteudo_grande = b"x" * (25 * 1024 * 1024 + 1)
    file_mock = UploadFile(filename="grande.pdf", file=io.BytesIO(conteudo_grande))
    with pytest.raises(ValueError, match="O arquivo excede o limite máximo permitido de 25MB."):
        service.adicionar_documento(1, file_mock)


def test_service_adicionar_documento_extensao_invalida():
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)

    file_mock = UploadFile(filename="script.exe", file=io.BytesIO(b"MZ\x90\x00"))
    with pytest.raises(ValueError, match="Extensão de arquivo não permitida"):
        service.adicionar_documento(1, file_mock)

    file_sem_ext = UploadFile(filename="semextensao", file=io.BytesIO(b"123"))
    with pytest.raises(ValueError, match="Extensão de arquivo não permitida"):
        service.adicionar_documento(1, file_sem_ext)


def test_service_adicionar_documento_conteudo_invalido():
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)

    file_mock = UploadFile(
        filename="falso.pdf", file=io.BytesIO(b"Este texto nao eh um pdf valido")
    )
    with pytest.raises(
        ValueError, match="O conteúdo do arquivo não corresponde a um formato válido."
    ):
        service.adicionar_documento(1, file_mock)


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_service_adicionar_documento_sucesso_pdf(mock_obter_url, mock_salvar):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    mock_salvar.return_value = "processos/1/arquivo.pdf"
    mock_obter_url.return_value = "http://minio/processos/1/arquivo.pdf"

    pdf_magic_bytes = b"%PDF-1.4\n%test pdf content"
    file_mock = UploadFile(filename="peticao.pdf", file=io.BytesIO(pdf_magic_bytes))

    doc_mock = Arquivo(
        arquivo_id=1,
        nome_arquivo="peticao.pdf",
        bucket_link="processos/1/arquivo.pdf",
        origem="manual",
        tamanho_bytes=len(pdf_magic_bytes),
        tipo_mime="application/pdf",
        funcionario_id=5,
        data_upload=datetime(2026, 1, 1),
    )
    service.repository.adicionar_documento.return_value = doc_mock

    res = service.adicionar_documento(1, file_mock, funcionario_id=5)

    assert res.documento_id == 1
    assert res.nome_original == "peticao.pdf"
    assert res.chave_minio == "processos/1/arquivo.pdf"
    assert res.origem == "manual"
    assert res.entrada_tipo == "application/pdf"
    assert res.url == "http://minio/processos/1/arquivo.pdf"
    mock_salvar.assert_called_once()
    service.repository.adicionar_documento.assert_called_once()


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_service_adicionar_documento_sucesso_docx(mock_obter_url, mock_salvar):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    mock_salvar.return_value = "processos/1/arquivo.docx"
    mock_obter_url.return_value = "http://minio/processos/1/arquivo.docx"

    docx_bytes = b"PK\x03\x04 fake docx content"
    file_mock = UploadFile(filename="contrato.docx", file=io.BytesIO(docx_bytes))

    doc_mock = Arquivo(
        arquivo_id=2,
        nome_arquivo="contrato.docx",
        bucket_link="processos/1/arquivo.docx",
        origem="manual",
        tamanho_bytes=len(docx_bytes),
        tipo_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        funcionario_id=None,
        data_upload=datetime(2026, 1, 1),
    )
    service.repository.adicionar_documento.return_value = doc_mock

    res = service.adicionar_documento(1, file_mock)

    assert res.documento_id == 2
    assert res.nome_original == "contrato.docx"
    assert res.origem == "manual"


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.remover_arquivo")
def test_service_adicionar_documento_erro_banco_chama_remover_arquivo(mock_remover, mock_salvar):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    mock_salvar.return_value = "processos/1/arquivo.pdf"

    service.repository.adicionar_documento.side_effect = Exception("Erro no banco")

    pdf_magic_bytes = b"%PDF-1.4\n%content"
    file_mock = UploadFile(filename="peticao.pdf", file=io.BytesIO(pdf_magic_bytes))

    with pytest.raises(Exception, match="Erro no banco"):
        service.adicionar_documento(1, file_mock)

    mock_remover.assert_called_once_with("processos/1/arquivo.pdf", bucket="privado")


def test_service_listar_documentos_processo_inexistente():
    service = criar_service()
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.listar_documentos(999)


@patch("app.processo.service.obter_url_publica")
def test_service_listar_documentos_sucesso(mock_obter_url):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    mock_obter_url.return_value = "http://minio/arquivo.pdf"

    doc = Arquivo(
        arquivo_id=1,
        nome_arquivo="peticao.pdf",
        bucket_link="processos/1/a.pdf",
        origem="manual",
        tamanho_bytes=100,
        tipo_mime="application/pdf",
        funcionario_id=None,
        data_upload=datetime(2026, 1, 1),
    )
    service.repository.listar_documentos.return_value = [doc]

    res = service.listar_documentos(1)

    assert len(res) == 1
    assert res[0].documento_id == 1
    assert res[0].origem == "manual"
    assert res[0].url == "http://minio/arquivo.pdf"


def test_service_obter_url_documento_inexistente():
    service = criar_service()
    service.repository.buscar_documento.return_value = None

    with pytest.raises(ValueError, match="Documento não encontrado"):
        service.obter_url_documento(1, 999)


@patch("app.processo.service.obter_url_publica")
def test_service_obter_url_documento_falha_geracao(mock_obter_url):
    service = criar_service()
    doc = MagicMock(bucket_link="processos/1/a.pdf")
    service.repository.buscar_documento.return_value = doc
    mock_obter_url.return_value = None

    with pytest.raises(ValueError, match="Falha ao gerar URL de acesso ao documento"):
        service.obter_url_documento(1, 10)


@patch("app.processo.service.obter_url_publica")
def test_service_obter_url_documento_sucesso(mock_obter_url):
    service = criar_service()
    doc = MagicMock(bucket_link="processos/1/a.pdf")
    service.repository.buscar_documento.return_value = doc
    mock_obter_url.return_value = "http://minio/download-presigned"

    url = service.obter_url_documento(1, 10, expiracao_segundos=600)

    assert url == "http://minio/download-presigned"
    mock_obter_url.assert_called_once_with(
        "processos/1/a.pdf", expiracao_segundos=600, bucket="privado"
    )


def test_service_remover_documento_inexistente():
    service = criar_service()
    service.repository.buscar_documento.return_value = None

    with pytest.raises(ValueError, match="Documento não encontrado"):
        service.remover_documento(1, 999)


@patch("app.processo.service.remover_arquivo")
def test_service_remover_documento_sucesso(mock_remover):
    service = criar_service()
    doc = MagicMock(bucket_link="processos/1/a.pdf")
    service.repository.buscar_documento.return_value = doc

    service.remover_documento(1, 10)

    service.repository.deletar_documento.assert_called_once_with(1, doc)
    mock_remover.assert_called_once_with("processos/1/a.pdf", bucket="privado")


@pytest.mark.parametrize(
    "nome_cargo,permissoes,sem_cargo,usuario_nulo,esperado",
    [
        ("Administrador", {}, False, False, True),
        ("  admin ", {}, False, False, True),
        ("Advogado Sênior", {"gerenciar_equipe": True}, False, False, True),
        ("Advogado Pleno", {"visualizar_processos": True}, False, False, False),
        ("", None, True, False, False),
        ("", None, False, True, True),
    ],
)
def test_service_eh_administrador_parametrizado(
    nome_cargo,
    permissoes,
    sem_cargo,
    usuario_nulo,
    esperado,
):
    if usuario_nulo:
        usuario = None
    else:
        usuario = MagicMock()
        if sem_cargo:
            usuario.cargo = None
        else:
            cargo = MagicMock()
            cargo.nome_cargo = nome_cargo
            cargo.permissao = permissoes
            usuario.cargo = cargo

    assert ProcessoService._eh_administrador(usuario) is esperado


@pytest.mark.parametrize(
    "eh_admin,usuario_id,filtro_param,dias_prazo,contagens_status,atrasados_mock,proximos_mock,filtro_esperado",
    [
        (
            True,
            1,
            None,
            7,
            {
                StatusProcesso.ATIVO: 4,
                StatusProcesso.EM_ANALISE: 2,
                StatusProcesso.CONCLUIDO: 3,
                StatusProcesso.ARQUIVADO: 1,
            },
            1,
            2,
            None,
        ),
        (
            True,
            1,
            25,
            15,
            {
                StatusProcesso.ATIVO: 2,
            },
            0,
            1,
            25,
        ),
        (
            False,
            10,
            99,
            7,
            {
                StatusProcesso.EM_ANALISE: 3,
                StatusProcesso.ARQUIVADO: 2,
            },
            2,
            0,
            10,
        ),
    ],
)
def test_service_obter_resumo_processos_parametrizado(
    eh_admin,
    usuario_id,
    filtro_param,
    dias_prazo,
    contagens_status,
    atrasados_mock,
    proximos_mock,
    filtro_esperado,
):
    service = criar_service()

    usuario = MagicMock()
    usuario.funcionario_id = usuario_id
    cargo = MagicMock()
    cargo.nome_cargo = "Administrador" if eh_admin else "Advogado"
    cargo.permissao = {"gerenciar_equipe": eh_admin}
    usuario.cargo = cargo

    service.repository.contar_por_status.return_value = contagens_status
    service.repository.contar_por_filtros.side_effect = [atrasados_mock, proximos_mock]

    resumo = service.obter_resumo_processos(
        usuario=usuario,
        funcionario_id=filtro_param,
        dias_proximo_prazo=dias_prazo,
    )

    em_andamento_esp = contagens_status.get(StatusProcesso.ATIVO, 0)
    em_analise_esp = contagens_status.get(StatusProcesso.EM_ANALISE, 0)
    finalizados_esp = contagens_status.get(StatusProcesso.CONCLUIDO, 0)

    assert resumo.em_andamento == em_andamento_esp
    assert resumo.em_analise == em_analise_esp
    assert resumo.finalizados == finalizados_esp
    assert resumo.total == em_andamento_esp + em_analise_esp + finalizados_esp
    assert resumo.atrasados == atrasados_mock
    assert resumo.proximos_do_prazo == proximos_mock

    service.repository.contar_por_status.assert_called_once_with(funcionario_id=filtro_esperado)
    assert service.repository.contar_por_filtros.call_count == 2


def test_service_listar_movimentacoes_processo_inexistente():
    service = criar_service()
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.listar_movimentacoes(999)


def test_service_listar_movimentacoes_sucesso():
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    movimentacao = ProcessoMovimentacao(
        movimentacao_id=1,
        processo_id=10,
        funcionario_id=2,
        tipo_movimentacao=TipoMovimentacaoProcesso.CRIACAO_PROCESSO,
        descricao="Processo criado.",
        data_movimentacao=datetime(2026, 1, 1),
    )
    service.repository.listar_movimentacoes.return_value = [movimentacao]

    resultado = service.listar_movimentacoes(10)

    assert len(resultado) == 1
    assert resultado[0].movimentacao_id == 1
    assert resultado[0].processo_id == 10
    assert resultado[0].tipo_movimentacao == TipoMovimentacaoProcesso.CRIACAO_PROCESSO
    service.repository.listar_movimentacoes.assert_called_once_with(10)


@patch("app.processo.service.salvar_arquivo")
@patch("app.processo.service.remover_arquivo")
@patch("app.processo.service.obter_url_publica")
def test_controller_fluxo_movimentacoes_processo_e_documentos(
    mock_url,
    mock_remover,
    mock_salvar,
    client,
    db_session,
    usuario_processos,
    cliente_processo,
    funcionario_responsavel,
):
    _, token = usuario_processos
    mock_salvar.return_value = "processos/1/doc.pdf"
    mock_url.return_value = "http://minio/doc.pdf"
    headers = auth_header(token)

    resposta_criacao = client.post(
        "/processos/",
        json={
            "cnj": "44444333332222211111",
            "titulo": "Processo Histórico",
            "descricao": "Descrição",
            "status": "Ativo",
            "tribunal": "TJDFT",
            "area": "Civil",
            "data_inicio": "2026-01-01T00:00:00",
            "data_prazo": "2026-12-31T00:00:00",
            "cliente_id": cliente_processo.cliente_id,
            "funcionario_id": funcionario_responsavel.funcionario_id,
        },
        headers=headers,
    )
    assert resposta_criacao.status_code == 201
    processo_id = resposta_criacao.json()["processo_id"]

    resposta_atualizacao = client.patch(
        f"/processos/{processo_id}",
        json={"status": "Concluído"},
        headers=headers,
    )
    assert resposta_atualizacao.status_code == 200

    resposta_upload = client.post(
        f"/processos/{processo_id}/documentos",
        headers=headers,
        files={"file": ("peticao.pdf", b"%PDF-1.4\n%content", "application/pdf")},
    )
    assert resposta_upload.status_code == 201
    documento_id = resposta_upload.json()["documento_id"]

    resposta_remocao = client.delete(
        f"/processos/{processo_id}/documentos/{documento_id}",
        headers=headers,
    )
    assert resposta_remocao.status_code == 204

    resposta_movimentacoes = client.get(
        f"/processos/{processo_id}/movimentacoes",
        headers=headers,
    )

    assert resposta_movimentacoes.status_code == 200
    assert [
        movimentacao["tipo_movimentacao"] for movimentacao in resposta_movimentacoes.json()
    ] == [
        "EXCLUSAO_ARQUIVO",
        "UPLOAD_ARQUIVO",
        "ATUALIZACAO_PROCESSO",
        "CRIACAO_PROCESSO",
    ]


def test_controller_listar_movimentacoes_processo_inexistente_retorna_404(
    client, usuario_processos
):
    _, token = usuario_processos

    resposta = client.get(
        "/processos/999999/movimentacoes",
        headers=auth_header(token),
    )

    assert resposta.status_code == 404
    assert "Processo não encontrado" in resposta.json()["detail"]


@pytest.fixture
def sync_db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    cliente = Cliente(
        nome="Cliente Sync",
        telefone="11999999999",
        email="sync@teste.com",
        area_interesse="Civil",
        etapa_id=1,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    yield db, cliente

    db.rollback()
    db.query(Processo).delete()
    db.query(Cliente).delete()
    db.commit()
    db.close()


@pytest.mark.asyncio
@patch("app.processo.service.DatajudApiClient.fetch_processo")
async def test_sync_sincronizar_processos_com_api(mock_fetch, sync_db_session):
    db, cliente = sync_db_session
    p1 = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        funcionario_id=1,
        cnj="123456789",
        titulo="Proc 1",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )
    p2 = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        funcionario_id=1,
        cnj="987654321",
        titulo="Proc 2",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )

    db.add(p1)
    db.add(p2)
    db.commit()

    mock_data = {
        "status": StatusProcesso.CONCLUIDO,
        "tribunal": "TJSP",
        "data_realizado": datetime(2026, 12, 1),
    }

    async def side_effect(cnj):
        if cnj == "123456789":
            return mock_data
        return None

    mock_fetch.side_effect = side_effect

    await ProcessoService.sincronizar_processos_com_api()

    db.refresh(p1)
    assert p1.status == StatusProcesso.CONCLUIDO
    assert p1.tribunal == "TJSP"
    assert p1.data_realizado == mock_data["data_realizado"]

    db.refresh(p2)
    assert p2.status == StatusProcesso.ATIVO


@pytest.mark.asyncio
@patch("app.processo.service.DatajudApiClient.fetch_processo")
async def test_sync_sincronizar_processos_com_api_empty_cnj(mock_fetch, sync_db_session):
    db, cliente = sync_db_session
    p1 = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        funcionario_id=1,
        cnj=" ",
        titulo="Proc vazio",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )
    p1.cnj = ""
    db.add(p1)
    db.commit()

    await ProcessoService.sincronizar_processos_com_api()
    mock_fetch.assert_not_called()


@pytest.mark.asyncio
@patch("app.processo.service.DatajudApiClient.fetch_processo")
async def test_sync_sincronizar_processos_com_api_exception(mock_fetch, sync_db_session):
    db, cliente = sync_db_session
    p1 = Processo(
        descricao="Descrição",
        data_inicio=datetime(2026, 1, 1),
        data_prazo=datetime(2026, 12, 31),
        funcionario_id=1,
        cnj="123",
        titulo="Proc",
        status=StatusProcesso.ATIVO,
        tribunal="TJSP",
        area="Civil",
        cliente_id=cliente.cliente_id,
    )
    db.add(p1)
    db.commit()

    mock_fetch.side_effect = Exception("Erro forçado")

    with pytest.raises(Exception, match="Erro forçado"):
        await ProcessoService.sincronizar_processos_com_api()

    db.refresh(p1)
    assert p1.status == StatusProcesso.ATIVO


@pytest.mark.parametrize("online,status_esperado", [(True, "online"), (False, "offline")])
def test_controller_verificar_status_datajud(
    client, db_session, token_acesso, online, status_esperado
):
    cargo = criar_cargo(db_session, {})
    usuario = criar_funcionario(db_session, cargo, f"status.{status_esperado}@test.com")
    token = token_acesso(usuario.funcionario_id, usuario.email)

    with patch(
        "app.processo.service.DatajudApiClient.verificar_status",
        return_value=online,
    ):
        response = client.get("/processos/datajud/status", headers=auth_header(token))

    assert response.status_code == 200
    dados = response.json()
    assert dados["online"] is online
    assert dados["status"] == status_esperado
    assert isinstance(dados["mensagem"], str)
