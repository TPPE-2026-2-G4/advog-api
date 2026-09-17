import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from PIL import Image

from app.models.institucional import Institucional
from app.repositories.institucional import InstitucionalRepository
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
