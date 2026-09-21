import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from PIL import Image
from pydantic import ValidationError

from app.models.institucional import Institucional
from app.repositories.institucional import InstitucionalRepository
from app.schemas.institucional import InstitucionalBase, InstitucionalResponse, InstitucionalUpdate
from app.services.funcionario import FuncionarioService
from app.services.institucional import InstitucionalService, UploadInvalidoError


@pytest.fixture
def service_mocked():
    service = InstitucionalService.__new__(InstitucionalService)
    service.repository = MagicMock(spec=InstitucionalRepository)
    return service


def test_obter_configuracoes_retorna_modelo(service_mocked):
    esperado = Institucional(institucional_id=1, nome_escritorio="Advocacia Teste")
    service_mocked.repository.buscar_configuracoes.return_value = esperado

    resultado = service_mocked.obter_configuracoes()

    assert resultado == esperado
    service_mocked.repository.buscar_configuracoes.assert_called_once()


def test_atualizar_configuracoes_filtra_valores_none(service_mocked):
    service_mocked.repository.atualizar_configuracoes.return_value = MagicMock()
    dados_input = {"nome_escritorio": "Novo Nome", "email": None}

    service_mocked.atualizar_configuracoes(dados_input)

    service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
        {"nome_escritorio": "Novo Nome"}
    )


def test_upload_midia_tipo_invalido_lanca_erro(service_mocked):
    file_mock = MagicMock(spec=UploadFile)

    with pytest.raises(UploadInvalidoError, match="Tipo de mídia inválido"):
        service_mocked.upload_midia(file_mock, "invalido")


def test_upload_logo_excede_tamanho_lanca_erro(service_mocked):
    conteudo_grande = b"0" * (2 * 1024 * 1024 + 1)
    file_mock = UploadFile(filename="logo.png", file=io.BytesIO(conteudo_grande))

    with pytest.raises(UploadInvalidoError, match="máximo 2MB"):
        service_mocked.upload_midia(file_mock, "logo")


def test_upload_banner_excede_tamanho_lanca_erro(service_mocked):
    conteudo_grande = b"0" * (5 * 1024 * 1024 + 1)
    file_mock = UploadFile(filename="banner.png", file=io.BytesIO(conteudo_grande))

    with pytest.raises(UploadInvalidoError, match="máximo 5MB"):
        service_mocked.upload_midia(file_mock, "banner")


def test_upload_svg_malicioso_com_script_lanca_erro(service_mocked):
    svg_malicioso = b'<svg><script>alert("xss")</script></svg>'
    file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_malicioso))

    with pytest.raises(UploadInvalidoError, match="contém scripts"):
        service_mocked.upload_midia(file_mock, "logo")


def test_upload_svg_malicioso_com_atributo_evento_lanca_erro(service_mocked):
    svg_malicioso = b'<svg width="100" height="100" onload="alert(1)"></svg>'
    file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_malicioso))

    with pytest.raises(UploadInvalidoError, match="executáveis inseguros"):
        service_mocked.upload_midia(file_mock, "logo")


@patch("app.services.institucional.salvar_arquivo")
@patch("app.services.institucional.remover_arquivo")
@patch("app.services.institucional.obter_url_publica")
def test_upload_banner_com_warning_resolucao(mock_url, mock_remover, mock_salvar, service_mocked):
    mock_salvar.return_value = "banners/123.png"
    mock_url.return_value = "http://localhost:9000/institucional/banners/123.png"
    service_mocked.repository.buscar_configuracoes.return_value = MagicMock(banner_hero=None)

    img = Image.new("RGB", (800, 400), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    file_mock = UploadFile(filename="banner.png", file=img_byte_arr)
    url, warning = service_mocked.upload_midia(file_mock, "banner")

    assert url == "http://localhost:9000/institucional/banners/123.png"
    assert warning is not None
    assert "abaixo da recomendada" in warning


@patch("app.services.institucional.salvar_arquivo")
@patch("app.services.institucional.remover_arquivo")
@patch("app.services.institucional.obter_url_publica")
def test_upload_logo_sucesso_com_remocao_antiga(
    mock_url, mock_remover, mock_salvar, service_mocked
):
    mock_salvar.return_value = "logotipos/novo.svg"
    mock_url.return_value = "http://localhost:9000/institucional/logotipos/novo.svg"

    config_mock = MagicMock(logotipo="logotipos/antigo.svg")
    service_mocked.repository.buscar_configuracoes.return_value = config_mock

    svg_valido = b'<svg width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
    file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_valido))

    url, warning = service_mocked.upload_midia(file_mock, "logo")

    assert url == "http://localhost:9000/institucional/logotipos/novo.svg"
    assert warning is None
    mock_remover.assert_called_once_with("logotipos/antigo.svg")
    service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
        {"logotipo": "logotipos/novo.svg"}
    )


def test_upload_sobre_excede_tamanho_lanca_erro(service_mocked):
    conteudo_grande = b"0" * (5 * 1024 * 1024 + 1)
    file_mock = UploadFile(filename="sobre.png", file=io.BytesIO(conteudo_grande))

    with pytest.raises(UploadInvalidoError, match="máximo 5MB"):
        service_mocked.upload_midia(file_mock, "sobre")


@patch("app.services.institucional.salvar_arquivo")
@patch("app.services.institucional.remover_arquivo")
@patch("app.services.institucional.obter_url_publica")
def test_upload_sobre_com_warning_resolucao(mock_url, mock_remover, mock_salvar, service_mocked):
    mock_salvar.return_value = "sobre/123.png"
    mock_url.return_value = "http://localhost:9000/institucional/sobre/123.png"
    service_mocked.repository.buscar_configuracoes.return_value = MagicMock(imagem_sobre=None)

    img = Image.new("RGB", (400, 300), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    file_mock = UploadFile(filename="sobre.png", file=img_byte_arr)
    url, warning = service_mocked.upload_midia(file_mock, "sobre")

    assert url == "http://localhost:9000/institucional/sobre/123.png"
    assert warning is not None
    assert "800x600px" in warning


@patch("app.services.institucional.salvar_arquivo")
@patch("app.services.institucional.remover_arquivo")
@patch("app.services.institucional.obter_url_publica")
def test_upload_sobre_sucesso_com_remocao_antiga(
    mock_url, mock_remover, mock_salvar, service_mocked
):
    mock_salvar.return_value = "sobre/novo.png"
    mock_url.return_value = "http://localhost:9000/institucional/sobre/novo.png"

    config_mock = MagicMock(imagem_sobre="sobre/antigo.png")
    service_mocked.repository.buscar_configuracoes.return_value = config_mock

    img = Image.new("RGB", (800, 600), color="green")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    file_mock = UploadFile(filename="sobre.png", file=img_byte_arr)

    url, warning = service_mocked.upload_midia(file_mock, "sobre")

    assert url == "http://localhost:9000/institucional/sobre/novo.png"
    assert warning is None
    mock_remover.assert_called_once_with("sobre/antigo.png")
    service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
        {"imagem_sobre": "sobre/novo.png"}
    )


def test_upload_logo_formato_invalido_lanca_erro(service_mocked):
    file_mock = UploadFile(
        filename="logo.jpg",
        file=io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF"),
    )
    with pytest.raises(UploadInvalidoError, match="PNG ou SVG válido"):
        service_mocked.upload_midia(file_mock, "logo")


def test_upload_banner_formato_invalido_lanca_erro(service_mocked):
    file_mock = UploadFile(filename="banner.txt", file=io.BytesIO(b"conteudo texto"))
    with pytest.raises(UploadInvalidoError, match="JPG ou PNG válida"):
        service_mocked.upload_midia(file_mock, "banner")


def test_upload_sobre_formato_invalido_lanca_erro(service_mocked):
    file_mock = UploadFile(filename="sobre.txt", file=io.BytesIO(b"conteudo texto"))
    with pytest.raises(UploadInvalidoError, match="JPG ou PNG válida"):
        service_mocked.upload_midia(file_mock, "sobre")


@patch("app.services.institucional.salvar_arquivo")
@patch("app.services.institucional.obter_url_publica")
def test_upload_banner_imagem_corrompida_trata_excecao_pillow(
    mock_url, mock_salvar, service_mocked
):
    mock_salvar.return_value = "banners/corrompido.png"
    mock_url.return_value = "http://localhost:9000/banners/corrompido.png"
    service_mocked.repository.buscar_configuracoes.return_value = MagicMock(banner_hero=None)

    conteudo_corrompido = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"0" * 100
    file_mock = UploadFile(filename="banner.png", file=io.BytesIO(conteudo_corrompido))

    url, warning = service_mocked.upload_midia(file_mock, "banner")
    assert url == "http://localhost:9000/banners/corrompido.png"
    assert warning is None


def test_schema_institucional_limpar_email_vazio():
    data = {
        "nomeEscritorio": "Escritório Modelo",
        "email": "",
        "corPrimaria": "#1E3A8A",
        "corSecundaria": "#B79A63",
    }
    schema = InstitucionalBase(**data)
    assert schema.email is None


def test_schema_institucional_cor_hex_invalida_lanca_erro():
    with pytest.raises(ValidationError, match="formato hexadecimal"):
        InstitucionalBase(
            nomeEscritorio="Escritório Modelo",
            corPrimaria="COR_INVALIDA",
            corSecundaria="#B79A63",
        )

    with pytest.raises(ValidationError, match="formato hexadecimal"):
        InstitucionalUpdate(corPrimaria="123456")


def test_schema_institucional_response_serializacao_midia():
    data = {
        "institucional_id": 1,
        "nomeEscritorio": "Escritório Modelo",
        "corPrimaria": "#1E3A8A",
        "corSecundaria": "#B79A63",
        "logotipo": "logotipos/logo.svg",
        "bannerHero": None,
        "imagemSobre": None,
    }
    schema = InstitucionalResponse.model_validate(data)
    json_data = schema.model_dump(by_alias=True)

    assert json_data["logotipo"] is not None
    assert json_data["bannerHero"] is None
    assert json_data["imagemSobre"] is None


def test_schema_institucional_update_limpar_email_vazio_e_validar_hex_valido():
    schema_email = InstitucionalUpdate(email="")
    assert schema_email.email is None

    schema_hex = InstitucionalUpdate(corPrimaria="#1E3A8A", corSecundaria="#B79A63")
    assert schema_hex.cor_primaria == "#1E3A8A"
    assert schema_hex.cor_secundaria == "#B79A63"


def test_mudar_exibicao_institucional_funcionario_nao_encontrado_lanca_erro(db_session):
    service = FuncionarioService(db_session)
    with pytest.raises(ValueError, match="Funcionário não encontrado"):
        service.mudar_exibicao_institucional(9999, True)


def test_upload_svg_com_atributo_javascript_inseguro_lanca_erro(service_mocked):
    svg_inseguro = b'<svg><a href="javascript:alert(1)">Click</a></svg>'
    file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_inseguro))

    with pytest.raises(UploadInvalidoError, match="executáveis inseguros"):
        service_mocked.upload_midia(file_mock, "logo")


def test_upload_svg_corrompido_lanca_erro(service_mocked):
    svg_corrompido = b"<svg><tag_invalida_sem_fechamento>"
    file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_corrompido))

    with pytest.raises(UploadInvalidoError, match="corrompido ou inválido"):
        service_mocked.upload_midia(file_mock, "logo")


def test_upload_svg_com_namespace_e_atributos_validos(service_mocked):
    svg_ns = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
    file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_ns))
    service_mocked.repository.buscar_configuracoes.return_value = MagicMock(logotipo=None)

    with (
        patch("app.services.institucional.salvar_arquivo", return_value="logotipos/ns.svg"),
        patch(
            "app.services.institucional.obter_url_publica",
            return_value="http://localhost:9000/logotipos/ns.svg",
        ),
    ):
        url, warning = service_mocked.upload_midia(file_mock, "logo")
        assert url == "http://localhost:9000/logotipos/ns.svg"
        assert warning is None
