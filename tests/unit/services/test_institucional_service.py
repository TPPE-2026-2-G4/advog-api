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


def _gerar_imagem_bytes(
    largura: int, altura: int, cor: str = "red", formato: str = "PNG"
) -> io.BytesIO:
    img = Image.new("RGB", (largura, altura), color=cor)
    buffer = io.BytesIO()
    img.save(buffer, format=formato)
    buffer.seek(0)
    return buffer


class TestInstitucionalServiceConfiguracoes:
    def test_obter_configuracoes_retorna_modelo(self, service_mocked):
        esperado = Institucional(institucional_id=1, nome_escritorio="Advocacia Teste")
        service_mocked.repository.buscar_configuracoes.return_value = esperado

        resultado = service_mocked.obter_configuracoes()

        assert resultado == esperado
        service_mocked.repository.buscar_configuracoes.assert_called_once()

    def test_atualizar_configuracoes_filtra_valores_none(self, service_mocked):
        service_mocked.repository.atualizar_configuracoes.return_value = MagicMock()
        dados_input = {"nome_escritorio": "Novo Nome", "email": None}

        service_mocked.atualizar_configuracoes(dados_input)

        service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
            {"nome_escritorio": "Novo Nome"}
        )


class TestInstitucionalServiceUploadValidacoes:
    def test_upload_midia_tipo_invalido_lanca_erro(self, service_mocked):
        file_mock = MagicMock(spec=UploadFile)
        with pytest.raises(UploadInvalidoError, match="Tipo de mídia inválido"):
            service_mocked.upload_midia(file_mock, "invalido")

    @pytest.mark.parametrize(
        "tipo,tamanho_mb,filename",
        [
            ("logo", 2, "logo.png"),
            ("banner", 5, "banner.png"),
            ("sobre", 5, "sobre.png"),
        ],
    )
    def test_upload_midia_excede_tamanho_lanca_erro(
        self, service_mocked, tipo, tamanho_mb, filename
    ):
        conteudo_grande = b"0" * (tamanho_mb * 1024 * 1024 + 1)
        file_mock = UploadFile(filename=filename, file=io.BytesIO(conteudo_grande))

        with pytest.raises(UploadInvalidoError, match=f"máximo {tamanho_mb}MB"):
            service_mocked.upload_midia(file_mock, tipo)

    @pytest.mark.parametrize(
        "tipo,filename,conteudo,mensagem_erro",
        [
            (
                "logo",
                "logo.jpg",
                b"\xff\xd8\xff\xe0\x00\x10JFIF",
                "PNG ou SVG válido",
            ),
            ("banner", "banner.txt", b"conteudo texto", "JPG ou PNG válida"),
            ("sobre", "sobre.txt", b"conteudo texto", "JPG ou PNG válida"),
        ],
    )
    def test_upload_midia_formato_invalido_lanca_erro(
        self, service_mocked, tipo, filename, conteudo, mensagem_erro
    ):
        file_mock = UploadFile(filename=filename, file=io.BytesIO(conteudo))
        with pytest.raises(UploadInvalidoError, match=mensagem_erro):
            service_mocked.upload_midia(file_mock, tipo)

    @pytest.mark.parametrize(
        "svg_conteudo,mensagem_erro",
        [
            (b'<svg><script>alert("xss")</script></svg>', "contém scripts"),
            (
                b'<svg width="100" height="100" onload="alert(1)"></svg>',
                "executáveis inseguros",
            ),
            (
                b'<svg><a href="javascript:alert(1)">Click</a></svg>',
                "executáveis inseguros",
            ),
            (b"<svg><tag_invalida_sem_fechamento>", "corrompido ou inválido"),
        ],
    )
    def test_upload_svg_invalido_ou_malicioso_lanca_erro(
        self, service_mocked, svg_conteudo, mensagem_erro
    ):
        file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_conteudo))
        with pytest.raises(UploadInvalidoError, match=mensagem_erro):
            service_mocked.upload_midia(file_mock, "logo")


class TestInstitucionalServiceUploadProcessamento:
    @patch("app.services.institucional.salvar_arquivo")
    @patch("app.services.institucional.remover_arquivo")
    @patch("app.services.institucional.obter_url_publica")
    def test_upload_logo_sucesso_com_remocao_antiga(
        self, mock_url, mock_remover, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "logotipos/novo.svg"
        mock_url.return_value = "http://localhost:9000/institucional/logotipos/novo.svg"
        service_mocked.repository.buscar_configuracoes.return_value = MagicMock(
            logotipo="logotipos/antigo.svg"
        )

        svg_valido = b'<svg width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
        file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_valido))

        url, warning = service_mocked.upload_midia(file_mock, "logo")

        assert url == "http://localhost:9000/institucional/logotipos/novo.svg"
        assert warning is None
        mock_remover.assert_called_once_with("logotipos/antigo.svg")
        service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
            {"logotipo": "logotipos/novo.svg"}
        )

    def test_upload_svg_com_namespace_e_atributos_validos(self, service_mocked):
        svg_ns = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
        file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_ns))
        service_mocked.repository.buscar_configuracoes.return_value = MagicMock(logotipo=None)

        with (
            patch(
                "app.services.institucional.salvar_arquivo",
                return_value="logotipos/ns.svg",
            ),
            patch(
                "app.services.institucional.obter_url_publica",
                return_value="http://localhost:9000/logotipos/ns.svg",
            ),
        ):
            url, warning = service_mocked.upload_midia(file_mock, "logo")

            assert url == "http://localhost:9000/logotipos/ns.svg"
            assert warning is None

    @patch("app.services.institucional.salvar_arquivo")
    @patch("app.services.institucional.remover_arquivo")
    @patch("app.services.institucional.obter_url_publica")
    def test_upload_banner_com_warning_resolucao(
        self, mock_url, mock_remover, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "banners/123.png"
        mock_url.return_value = "http://localhost:9000/institucional/banners/123.png"
        service_mocked.repository.buscar_configuracoes.return_value = MagicMock(banner_hero=None)

        buffer_img = _gerar_imagem_bytes(800, 400, cor="red")
        file_mock = UploadFile(filename="banner.png", file=buffer_img)

        url, warning = service_mocked.upload_midia(file_mock, "banner")

        assert url == "http://localhost:9000/institucional/banners/123.png"
        assert warning is not None
        assert "abaixo da recomendada" in warning

    @patch("app.services.institucional.salvar_arquivo")
    @patch("app.services.institucional.obter_url_publica")
    def test_upload_banner_imagem_corrompida_trata_excecao_pillow(
        self, mock_url, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "banners/corrompido.png"
        mock_url.return_value = "http://localhost:9000/banners/corrompido.png"
        service_mocked.repository.buscar_configuracoes.return_value = MagicMock(banner_hero=None)

        conteudo_corrompido = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"0" * 100
        file_mock = UploadFile(filename="banner.png", file=io.BytesIO(conteudo_corrompido))

        url, warning = service_mocked.upload_midia(file_mock, "banner")

        assert url == "http://localhost:9000/banners/corrompido.png"
        assert warning is None

    @patch("app.services.institucional.salvar_arquivo")
    @patch("app.services.institucional.remover_arquivo")
    @patch("app.services.institucional.obter_url_publica")
    def test_upload_sobre_com_warning_resolucao(
        self, mock_url, mock_remover, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "sobre/123.png"
        mock_url.return_value = "http://localhost:9000/institucional/sobre/123.png"
        service_mocked.repository.buscar_configuracoes.return_value = MagicMock(imagem_sobre=None)

        buffer_img = _gerar_imagem_bytes(400, 300, cor="blue")
        file_mock = UploadFile(filename="sobre.png", file=buffer_img)

        url, warning = service_mocked.upload_midia(file_mock, "sobre")

        assert url == "http://localhost:9000/institucional/sobre/123.png"
        assert warning is not None
        assert "800x600px" in warning

    @patch("app.services.institucional.salvar_arquivo")
    @patch("app.services.institucional.remover_arquivo")
    @patch("app.services.institucional.obter_url_publica")
    def test_upload_sobre_sucesso_com_remocao_antiga(
        self, mock_url, mock_remover, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "sobre/novo.png"
        mock_url.return_value = "http://localhost:9000/institucional/sobre/novo.png"
        service_mocked.repository.buscar_configuracoes.return_value = MagicMock(
            imagem_sobre="sobre/antigo.png"
        )

        buffer_img = _gerar_imagem_bytes(800, 600, cor="green")
        file_mock = UploadFile(filename="sobre.png", file=buffer_img)

        url, warning = service_mocked.upload_midia(file_mock, "sobre")

        assert url == "http://localhost:9000/institucional/sobre/novo.png"
        assert warning is None
        mock_remover.assert_called_once_with("sobre/antigo.png")
        service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
            {"imagem_sobre": "sobre/novo.png"}
        )
