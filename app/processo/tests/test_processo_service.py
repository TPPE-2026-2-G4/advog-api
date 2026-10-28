import io
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile

from app.processo.model import DocumentoProcesso, Processo, StatusProcesso
from app.processo.schema import ProcessoCreate, ProcessoFilter, ProcessoUpdate
from app.processo.service import ProcessoService


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
        cliente_id=1,
        funcionario_id=2,
    )


def test_buscar_todos():
    service = criar_service()

    processos = [MagicMock(spec=Processo)]
    service.repository.buscar_todos.return_value = processos

    resultado = service.buscar_todos()

    assert resultado == processos
    service.repository.buscar_todos.assert_called_once()


def test_buscar_processos():
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


def test_buscar_processos_com_paginacao():
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
            processo_id=6,
            cnj="66666666666666666666",
            titulo="Processo 6",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=1,
        ),
        Processo(
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


def test_buscar_processos_sem_resultado():
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


def test_criar_processo():
    service = criar_service()

    dados = dados_processo_create()

    service.repository.buscar_por_cnj.return_value = None

    processo_criado = MagicMock(spec=Processo)
    service.repository.criar.return_value = processo_criado

    resultado = service.criar_processo(dados)

    assert resultado == processo_criado

    service.repository.buscar_por_cnj.assert_called_once_with(dados.cnj)
    service.repository.criar.assert_called_once()


def test_criar_processo_com_cnj_existente():
    service = criar_service()

    dados = dados_processo_create()

    processo_existente = MagicMock(spec=Processo)

    service.repository.buscar_por_cnj.return_value = processo_existente

    with pytest.raises(ValueError, match="Processo já cadastrado"):
        service.criar_processo(dados)

    service.repository.criar.assert_not_called()


def test_atualizar_processo():
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


def test_atualizar_processo_inexistente():
    service = criar_service()

    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.atualizar_processo(
            999,
            ProcessoUpdate(titulo="Teste"),
        )

    service.repository.atualizar.assert_not_called()


def test_atualizar_processo_com_cnj_duplicado():
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


def test_atualizar_processo_com_mesmo_cnj():
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
def test_deletar_processo(mock_remover):
    service = criar_service()

    processo = MagicMock(spec=Processo)
    doc = MagicMock(chave_minio="processos/1/doc.pdf")

    service.repository.buscar_por_id.return_value = processo
    service.repository.listar_documentos.return_value = [doc]

    service.deletar_processo(1)

    mock_remover.assert_called_once_with("processos/1/doc.pdf")
    service.repository.deletar.assert_called_once_with(processo)


def test_deletar_processo_inexistente():
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
def test_buscar_processos_criticos_parametrizado(dias, func_id):
    service = criar_service()
    processos = [
        Processo(
            processo_id=1,
            cnj="11111111111111111111",
            titulo="Proc Crítico",
            status=StatusProcesso.ATIVO,
            tribunal="TJSP",
            area="Civil",
            cliente_id=1,
            funcionario_id=func_id,
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


def test_adicionar_documento_processo_inexistente():
    service = criar_service()
    service.repository.buscar_por_id.return_value = None

    file_mock = MagicMock(spec=UploadFile)
    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.adicionar_documento(999, file_mock)


def test_adicionar_documento_arquivo_vazio():
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)

    file_mock = UploadFile(filename="vazio.pdf", file=io.BytesIO(b""))
    with pytest.raises(ValueError, match="O arquivo enviado está vazio."):
        service.adicionar_documento(1, file_mock)


def test_adicionar_documento_tamanho_excedido():
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)

    conteudo_grande = b"x" * (25 * 1024 * 1024 + 1)
    file_mock = UploadFile(filename="grande.pdf", file=io.BytesIO(conteudo_grande))
    with pytest.raises(ValueError, match="O arquivo excede o limite máximo permitido de 25MB."):
        service.adicionar_documento(1, file_mock)


def test_adicionar_documento_extensao_invalida():
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)

    file_mock = UploadFile(filename="script.exe", file=io.BytesIO(b"MZ\x90\x00"))
    with pytest.raises(ValueError, match="Extensão de arquivo não permitida"):
        service.adicionar_documento(1, file_mock)

    file_sem_ext = UploadFile(filename="semextensao", file=io.BytesIO(b"123"))
    with pytest.raises(ValueError, match="Extensão de arquivo não permitida"):
        service.adicionar_documento(1, file_sem_ext)


def test_adicionar_documento_conteudo_invalido():
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
def test_adicionar_documento_sucesso_pdf(mock_obter_url, mock_salvar):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    mock_salvar.return_value = "processos/1/arquivo.pdf"
    mock_obter_url.return_value = "http://minio/processos/1/arquivo.pdf"

    pdf_magic_bytes = b"%PDF-1.4\n%test pdf content"
    file_mock = UploadFile(filename="peticao.pdf", file=io.BytesIO(pdf_magic_bytes))

    doc_mock = DocumentoProcesso(
        documento_id=1,
        processo_id=1,
        nome_original="peticao.pdf",
        chave_minio="processos/1/arquivo.pdf",
        origem="manual",
        tamanho_bytes=len(pdf_magic_bytes),
        entrada_tipo="application/pdf",
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
def test_adicionar_documento_sucesso_docx(mock_obter_url, mock_salvar):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    mock_salvar.return_value = "processos/1/arquivo.docx"
    mock_obter_url.return_value = "http://minio/processos/1/arquivo.docx"

    docx_bytes = b"PK\x03\x04 fake docx content"
    file_mock = UploadFile(filename="contrato.docx", file=io.BytesIO(docx_bytes))

    doc_mock = DocumentoProcesso(
        documento_id=2,
        processo_id=1,
        nome_original="contrato.docx",
        chave_minio="processos/1/arquivo.docx",
        origem="manual",
        tamanho_bytes=len(docx_bytes),
        entrada_tipo="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
def test_adicionar_documento_erro_banco_chama_remover_arquivo(mock_remover, mock_salvar):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    mock_salvar.return_value = "processos/1/arquivo.pdf"

    service.repository.adicionar_documento.side_effect = Exception("Erro no banco")

    pdf_magic_bytes = b"%PDF-1.4\n%content"
    file_mock = UploadFile(filename="peticao.pdf", file=io.BytesIO(pdf_magic_bytes))

    with pytest.raises(Exception, match="Erro no banco"):
        service.adicionar_documento(1, file_mock)

    mock_remover.assert_called_once_with("processos/1/arquivo.pdf")


def test_listar_documentos_processo_inexistente():
    service = criar_service()
    service.repository.buscar_por_id.return_value = None

    with pytest.raises(ValueError, match="Processo não encontrado"):
        service.listar_documentos(999)


@patch("app.processo.service.obter_url_publica")
def test_listar_documentos_sucesso(mock_obter_url):
    service = criar_service()
    service.repository.buscar_por_id.return_value = MagicMock(spec=Processo)
    mock_obter_url.return_value = "http://minio/arquivo.pdf"

    doc = DocumentoProcesso(
        documento_id=1,
        processo_id=1,
        nome_original="peticao.pdf",
        chave_minio="processos/1/a.pdf",
        origem="manual",
        tamanho_bytes=100,
        entrada_tipo="application/pdf",
        funcionario_id=None,
        data_upload=datetime(2026, 1, 1),
    )
    service.repository.listar_documentos.return_value = [doc]

    res = service.listar_documentos(1)

    assert len(res) == 1
    assert res[0].documento_id == 1
    assert res[0].origem == "manual"
    assert res[0].url == "http://minio/arquivo.pdf"


def test_obter_url_documento_inexistente():
    service = criar_service()
    service.repository.buscar_documento_por_id.return_value = None

    with pytest.raises(ValueError, match="Documento não encontrado"):
        service.obter_url_documento(1, 999)


def test_obter_url_documento_processo_diferente():
    service = criar_service()
    doc = MagicMock(processo_id=2)
    service.repository.buscar_documento_por_id.return_value = doc

    with pytest.raises(ValueError, match="Documento não encontrado"):
        service.obter_url_documento(1, 10)


@patch("app.processo.service.obter_url_publica")
def test_obter_url_documento_falha_geracao(mock_obter_url):
    service = criar_service()
    doc = MagicMock(processo_id=1, chave_minio="processos/1/a.pdf")
    service.repository.buscar_documento_por_id.return_value = doc
    mock_obter_url.return_value = None

    with pytest.raises(ValueError, match="Falha ao gerar URL de acesso ao documento"):
        service.obter_url_documento(1, 10)


@patch("app.processo.service.obter_url_publica")
def test_obter_url_documento_sucesso(mock_obter_url):
    service = criar_service()
    doc = MagicMock(processo_id=1, chave_minio="processos/1/a.pdf")
    service.repository.buscar_documento_por_id.return_value = doc
    mock_obter_url.return_value = "http://minio/download-presigned"

    url = service.obter_url_documento(1, 10, expiracao_segundos=600)

    assert url == "http://minio/download-presigned"
    mock_obter_url.assert_called_once_with("processos/1/a.pdf", expiracao_segundos=600)


def test_remover_documento_inexistente():
    service = criar_service()
    service.repository.buscar_documento_por_id.return_value = None

    with pytest.raises(ValueError, match="Documento não encontrado"):
        service.remover_documento(1, 999)


def test_remover_documento_processo_diferente():
    service = criar_service()
    doc = MagicMock(processo_id=2)
    service.repository.buscar_documento_por_id.return_value = doc

    with pytest.raises(ValueError, match="Documento não encontrado"):
        service.remover_documento(1, 10)


@patch("app.processo.service.remover_arquivo")
def test_remover_documento_sucesso(mock_remover):
    service = criar_service()
    doc = MagicMock(processo_id=1, chave_minio="processos/1/a.pdf")
    service.repository.buscar_documento_por_id.return_value = doc

    service.remover_documento(1, 10)

    service.repository.deletar_documento.assert_called_once_with(doc)
    mock_remover.assert_called_once_with("processos/1/a.pdf")


@pytest.mark.parametrize(
    "nome_cargo,permissoes,sem_cargo,usuario_nulo,esperado",
    [
        ("Administrador", {}, False, False, True),
        ("  admin ", {}, False, False, True),
        ("Advogado Sênior", {"configuracoes_sistema": True}, False, False, True),
        ("Advogado Pleno", {"visualizar_processos": True}, False, False, False),
        ("", None, True, False, False),
        ("", None, False, True, True),
    ],
)
def test_eh_administrador_parametrizado(
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
def test_obter_resumo_processos_parametrizado(
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
    cargo.permissao = {"configuracoes_sistema": eh_admin}
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

