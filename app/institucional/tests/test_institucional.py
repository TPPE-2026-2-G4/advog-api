import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from PIL import Image
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.arquivo.model import Arquivo
from app.arquivo.repository import ArquivoRepository
from app.cargo.model import Cargo
from app.core.seguranca import criar_token_acesso
from app.funcionario.model import Funcionario, StatusFuncionario
from app.funcionario.service import FuncionarioService
from app.institucional.model import Institucional
from app.institucional.repository import (
    InstitucionalNaoEncontradoError,
    InstitucionalRepository,
)
from app.institucional.schema import (
    InstitucionalBase,
    InstitucionalResponse,
    InstitucionalUpdate,
    MembroEquipePublicaResponse,
)
from app.institucional.service import InstitucionalService, UploadInvalidoError


@pytest.fixture
def seed_institucional_db(institucional_padrao):
    return institucional_padrao


@pytest.fixture
def token_admin(db_session: Session):
    cargo = Cargo(
        nome_cargo="Administrador",
        permissao={"gerenciar_site": True},
    )
    db_session.add(cargo)
    db_session.commit()

    admin = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="Admin Teste",
        email="admin@teste.com",
        cargo_id=cargo.cargo_id,
        status=StatusFuncionario.ATIVO,
    )
    db_session.add(admin)
    db_session.commit()

    return criar_token_acesso({"sub": str(admin.funcionario_id), "email": admin.email})


@pytest.fixture
def token_sem_permissao(db_session: Session):
    cargo = Cargo(
        nome_cargo="Assistente",
        permissao={"gerenciar_site": False},
    )
    db_session.add(cargo)
    db_session.commit()

    user = Funcionario(
        atuacao_id=1,
        foto_perfil=1,
        nome="User Comum",
        email="user@teste.com",
        cargo_id=cargo.cargo_id,
        status=StatusFuncionario.ATIVO,
    )
    db_session.add(user)
    db_session.commit()

    return criar_token_acesso({"sub": str(user.funcionario_id), "email": user.email})


def _gerar_upload_file(filename: str = "imagem.png"):
    return {
        "file": (
            filename,
            io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"),
            "image/png",
        )
    }


class TestObterInstitucionalController:
    def test_obter_configuracoes_publicas_sucesso(self, client, seed_institucional_db):
        response = client.get("/institucional")

        assert response.status_code == 200
        assert response.json()["nomeEscritorio"] == "Escritório Modelo"

    def test_obter_equipe_publica_retorna_apenas_funcionarios_visiveis(self, client, db_session):
        cargo = Cargo(nome_cargo="Advogado", permissao={})
        db_session.add(cargo)
        db_session.commit()

        f1 = Funcionario(
            atuacao_id=1,
            foto_perfil=1,
            nome="Dr. Alexandre",
            email="alexandre@teste.com",
            cargo_id=cargo.cargo_id,
            status=StatusFuncionario.ATIVO,
            exibicao_institucional=True,
        )
        f2 = Funcionario(
            atuacao_id=1,
            foto_perfil=1,
            nome="Dra. Ana",
            email="ana@teste.com",
            cargo_id=cargo.cargo_id,
            status=StatusFuncionario.ATIVO,
            exibicao_institucional=False,
        )
        f3 = Funcionario(
            atuacao_id=1,
            foto_perfil=1,
            nome="Dr. Pedro Inativo",
            email="pedro@teste.com",
            cargo_id=cargo.cargo_id,
            status=StatusFuncionario.INATIVO,
            exibicao_institucional=True,
        )
        db_session.add_all([f1, f2, f3])
        db_session.commit()

        response = client.get("/institucional/equipe")

        assert response.status_code == 200
        dados = response.json()
        assert len(dados) == 1
        assert dados[0]["nome"] == "Dr. Alexandre"
        assert "exibicaoInstitucional" not in dados[0]


class TestAtualizarInstitucionalController:
    def test_atualizar_configuracoes_sem_token_retorna_401(self, client):
        response = client.put("/institucional", json={"nomeEscritorio": "Novo"})

        assert response.status_code == 401

    def test_atualizar_configuracoes_sem_permissao_retorna_403(self, client, token_sem_permissao):
        headers = {"Authorization": f"Bearer {token_sem_permissao}"}

        response = client.put("/institucional", json={"nomeEscritorio": "Novo"}, headers=headers)

        assert response.status_code == 403

    @pytest.mark.parametrize(
        "payload,campo_verificado,valor_esperado",
        [
            (
                {"nomeEscritorio": "Escritório Atualizado"},
                "nomeEscritorio",
                "Escritório Atualizado",
            ),
            (
                {
                    "sobreEscritorio": "Fundado em 2010...",
                    "textoAdicionalSobre": "Mais de 500 casos atendidos · 15 anos de atuação",
                },
                "sobreEscritorio",
                "Fundado em 2010...",
            ),
        ],
    )
    def test_atualizar_configuracoes_com_token_admin_sucesso(
        self,
        client,
        seed_institucional_db,
        token_admin,
        payload,
        campo_verificado,
        valor_esperado,
    ):
        headers = {"Authorization": f"Bearer {token_admin}"}

        response = client.put("/institucional", json=payload, headers=headers)

        assert response.status_code == 200
        assert response.json()[campo_verificado] == valor_esperado


class TestUploadMidiaInstitucionalController:
    @pytest.mark.parametrize("tipo,pasta", [("logo", "logotipos"), ("sobre", "sobre")])
    @patch("app.institucional.service.salvar_arquivo")
    @patch("app.institucional.service.obter_url_publica")
    def test_upload_midia_sucesso(
        self,
        mock_url,
        mock_salvar,
        client,
        seed_institucional_db,
        token_admin,
        tipo,
        pasta,
    ):
        mock_salvar.return_value = f"{pasta}/imagem_teste.png"
        mock_url.return_value = f"http://localhost:9000/institucional/{pasta}/imagem_teste.png"

        headers = {"Authorization": f"Bearer {token_admin}"}
        files = _gerar_upload_file(f"{tipo}.png")

        response = client.post(f"/institucional/upload/{tipo}", files=files, headers=headers)

        assert response.status_code == 200
        assert (
            response.json()["url"]
            == f"http://localhost:9000/institucional/{pasta}/imagem_teste.png"
        )

    @patch("app.institucional.service.remover_arquivo")
    @patch("app.institucional.service.salvar_arquivo")
    @patch("app.institucional.service.obter_url_publica")
    def test_upload_registra_arquivo_e_substitui_o_anterior(
        self,
        mock_url,
        mock_salvar,
        mock_remover,
        client,
        db_session,
        seed_institucional_db,
        token_admin,
    ):
        mock_url.return_value = "http://localhost:9000/logo"
        headers = {"Authorization": f"Bearer {token_admin}"}
        arquivo_padrao_id = seed_institucional_db.imagem_logotipo

        mock_salvar.return_value = "logotipos/primeiro.png"
        client.post(
            "/institucional/upload/logo", files=_gerar_upload_file("a.png"), headers=headers
        )
        db_session.refresh(seed_institucional_db)
        primeiro_id = seed_institucional_db.imagem_logotipo
        assert primeiro_id != arquivo_padrao_id
        assert seed_institucional_db.link_logotipo == "logotipos/primeiro.png"
        assert db_session.get(Arquivo, primeiro_id).nome_arquivo == "a.png"
        mock_remover.assert_not_called()  # o arquivo anterior era o padrão, compartilhado

        mock_salvar.return_value = "logotipos/segundo.png"
        client.post(
            "/institucional/upload/logo", files=_gerar_upload_file("b.png"), headers=headers
        )
        db_session.refresh(seed_institucional_db)
        assert seed_institucional_db.link_logotipo == "logotipos/segundo.png"
        assert db_session.get(Arquivo, primeiro_id) is None
        mock_remover.assert_called_once_with("logotipos/primeiro.png")
        assert db_session.get(Arquivo, arquivo_padrao_id) is not None

    def test_upload_tipo_invalido_retorna_400(self, client, token_admin):
        headers = {"Authorization": f"Bearer {token_admin}"}
        files = {"file": ("teste.txt", io.BytesIO(b"conteudo"), "text/plain")}

        response = client.post("/institucional/upload/invalido", files=files, headers=headers)

        assert response.status_code == 400


def _criar_institucional(db_session, arquivo_padrao, **campos) -> Institucional:
    config = Institucional(
        institucional_id=1,
        imagem_logotipo=arquivo_padrao.arquivo_id,
        banner_hero=arquivo_padrao.arquivo_id,
        imagem_sobre_escritorio=arquivo_padrao.arquivo_id,
        **campos,
    )
    db_session.add(config)
    db_session.commit()
    return config


def test_buscar_configuracoes_sucesso(db_session, arquivo_padrao):
    repository = InstitucionalRepository(db_session)
    sobre = Arquivo(
        nome_arquivo="foto_inicial.jpg",
        tipo_mime="image/jpeg",
        tamanho_bytes=10,
        bucket_link="sobre/foto_inicial.jpg",
    )
    db_session.add(sobre)
    db_session.commit()
    config = _criar_institucional(db_session, arquivo_padrao, nome_escritorio="Escritório Teste")
    config.imagem_sobre_escritorio = sobre.arquivo_id
    db_session.commit()

    resultado = repository.buscar_configuracoes()
    assert resultado.institucional_id == 1
    assert resultado.nome_escritorio == "Escritório Teste"
    assert resultado.link_imagem_sobre == "sobre/foto_inicial.jpg"
    assert resultado.link_logotipo == ""
    assert resultado.link_banner == ""
    assert resultado.atualizado_em is not None


def test_atualizar_configuracoes_sucesso(db_session, arquivo_padrao):
    repository = InstitucionalRepository(db_session)
    config = _criar_institucional(db_session, arquivo_padrao, nome_escritorio="Antigo")
    atualizado_antes = config.atualizado_em

    atualizado = repository.atualizar_configuracoes({"nome_escritorio": "Novo", "invalido": "x"})

    assert atualizado.nome_escritorio == "Novo"
    assert atualizado.atualizado_em >= atualizado_antes


def test_registro_institucional_e_singleton(db_session, arquivo_padrao):
    from sqlalchemy.exc import IntegrityError

    db_session.add(
        Institucional(
            institucional_id=2,
            imagem_logotipo=arquivo_padrao.arquivo_id,
            banner_hero=arquivo_padrao.arquivo_id,
            imagem_sobre_escritorio=arquivo_padrao.arquivo_id,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_buscar_configuracoes_inexistente_lanca_excesao(db_session):
    repository = InstitucionalRepository(db_session)
    with pytest.raises(InstitucionalNaoEncontradoError):
        repository.buscar_configuracoes()


def _config_com(atributo: str, bucket_link: str) -> MagicMock:
    return MagicMock(**{atributo: MagicMock(bucket_link=bucket_link)})


@pytest.fixture
def service_mocked():
    service = InstitucionalService.__new__(InstitucionalService)
    service.repository = MagicMock(spec=InstitucionalRepository)
    service.arquivo_repository = MagicMock(spec=ArquivoRepository)
    service.arquivo_repository.adicionar.return_value = MagicMock(arquivo_id=5)
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


@patch("app.institucional.service.salvar_arquivo")
@patch("app.institucional.service.remover_arquivo")
@patch("app.institucional.service.obter_url_publica")
def test_upload_banner_com_warning_resolucao(mock_url, mock_remover, mock_salvar, service_mocked):
    mock_salvar.return_value = "banners/123.png"
    mock_url.return_value = "http://localhost:9000/institucional/banners/123.png"
    service_mocked.repository.buscar_configuracoes.return_value = _config_com("arquivo_banner", "")

    img = Image.new("RGB", (800, 400), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    file_mock = UploadFile(filename="banner.png", file=img_byte_arr)
    url, warning = service_mocked.upload_midia(file_mock, "banner")

    assert url == "http://localhost:9000/institucional/banners/123.png"
    assert warning is not None
    assert "abaixo da recomendada" in warning


@patch("app.institucional.service.salvar_arquivo")
@patch("app.institucional.service.remover_arquivo")
@patch("app.institucional.service.obter_url_publica")
def test_upload_logo_sucesso_com_remocao_antiga(
    mock_url, mock_remover, mock_salvar, service_mocked
):
    mock_salvar.return_value = "logotipos/novo.svg"
    mock_url.return_value = "http://localhost:9000/institucional/logotipos/novo.svg"

    config_mock = _config_com("arquivo_logotipo", "logotipos/antigo.svg")
    service_mocked.repository.buscar_configuracoes.return_value = config_mock

    svg_valido = b'<svg width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
    file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_valido))

    url, warning = service_mocked.upload_midia(file_mock, "logo")

    assert url == "http://localhost:9000/institucional/logotipos/novo.svg"
    assert warning is None
    mock_remover.assert_called_once_with("logotipos/antigo.svg")
    service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
        {"imagem_logotipo": 5}
    )


def test_upload_sobre_excede_tamanho_lanca_erro(service_mocked):
    conteudo_grande = b"0" * (5 * 1024 * 1024 + 1)
    file_mock = UploadFile(filename="sobre.png", file=io.BytesIO(conteudo_grande))

    with pytest.raises(UploadInvalidoError, match="máximo 5MB"):
        service_mocked.upload_midia(file_mock, "sobre")


@patch("app.institucional.service.salvar_arquivo")
@patch("app.institucional.service.remover_arquivo")
@patch("app.institucional.service.obter_url_publica")
def test_upload_sobre_com_warning_resolucao(mock_url, mock_remover, mock_salvar, service_mocked):
    mock_salvar.return_value = "sobre/123.png"
    mock_url.return_value = "http://localhost:9000/institucional/sobre/123.png"
    service_mocked.repository.buscar_configuracoes.return_value = _config_com("arquivo_sobre", "")

    img = Image.new("RGB", (400, 300), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    file_mock = UploadFile(filename="sobre.png", file=img_byte_arr)
    url, warning = service_mocked.upload_midia(file_mock, "sobre")

    assert url == "http://localhost:9000/institucional/sobre/123.png"
    assert warning is not None
    assert "800x600px" in warning


@patch("app.institucional.service.salvar_arquivo")
@patch("app.institucional.service.remover_arquivo")
@patch("app.institucional.service.obter_url_publica")
def test_upload_sobre_sucesso_com_remocao_antiga(
    mock_url, mock_remover, mock_salvar, service_mocked
):
    mock_salvar.return_value = "sobre/novo.png"
    mock_url.return_value = "http://localhost:9000/institucional/sobre/novo.png"

    config_mock = _config_com("arquivo_sobre", "sobre/antigo.png")
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
        {"imagem_sobre_escritorio": 5}
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


@patch("app.institucional.service.salvar_arquivo")
@patch("app.institucional.service.obter_url_publica")
def test_upload_banner_imagem_corrompida_trata_excecao_pillow(
    mock_url, mock_salvar, service_mocked
):
    mock_salvar.return_value = "banners/corrompido.png"
    mock_url.return_value = "http://localhost:9000/banners/corrompido.png"
    service_mocked.repository.buscar_configuracoes.return_value = _config_com("arquivo_banner", "")

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
        "link_logotipo": "logotipos/logo.svg",
        "link_banner": "",
        "link_imagem_sobre": "",
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
    service_mocked.repository.buscar_configuracoes.return_value = _config_com(
        "arquivo_logotipo", ""
    )

    with (
        patch("app.institucional.service.salvar_arquivo", return_value="logotipos/ns.svg"),
        patch(
            "app.institucional.service.obter_url_publica",
            return_value="http://localhost:9000/logotipos/ns.svg",
        ),
    ):
        url, warning = service_mocked.upload_midia(file_mock, "logo")
        assert url == "http://localhost:9000/logotipos/ns.svg"
        assert warning is None


def test_schema_institucional_validador_entrada_nao_string():
    with pytest.raises(ValidationError):
        InstitucionalUpdate(email=12345)  # type: ignore


def test_membro_equipe_publica_schema_cargo_string_direta():
    membro = MembroEquipePublicaResponse(nome="Dr. Pedro", cargo="Advogado Sênior")
    assert membro.cargo == "Advogado Sênior"


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
    @patch("app.institucional.service.salvar_arquivo")
    @patch("app.institucional.service.remover_arquivo")
    @patch("app.institucional.service.obter_url_publica")
    def test_upload_logo_sucesso_com_remocao_antiga(
        self, mock_url, mock_remover, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "logotipos/novo.svg"
        mock_url.return_value = "http://localhost:9000/institucional/logotipos/novo.svg"
        service_mocked.repository.buscar_configuracoes.return_value = _config_com(
            "arquivo_logotipo", "logotipos/antigo.svg"
        )

        svg_valido = b'<svg width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
        file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_valido))

        url, warning = service_mocked.upload_midia(file_mock, "logo")

        assert url == "http://localhost:9000/institucional/logotipos/novo.svg"
        assert warning is None
        mock_remover.assert_called_once_with("logotipos/antigo.svg")
        service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
            {"imagem_logotipo": 5}
        )

    def test_upload_svg_com_namespace_e_atributos_validos(self, service_mocked):
        svg_ns = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
        file_mock = UploadFile(filename="logo.svg", file=io.BytesIO(svg_ns))
        service_mocked.repository.buscar_configuracoes.return_value = _config_com(
            "arquivo_logotipo", ""
        )

        with (
            patch(
                "app.institucional.service.salvar_arquivo",
                return_value="logotipos/ns.svg",
            ),
            patch(
                "app.institucional.service.obter_url_publica",
                return_value="http://localhost:9000/logotipos/ns.svg",
            ),
        ):
            url, warning = service_mocked.upload_midia(file_mock, "logo")

            assert url == "http://localhost:9000/logotipos/ns.svg"
            assert warning is None

    @patch("app.institucional.service.salvar_arquivo")
    @patch("app.institucional.service.remover_arquivo")
    @patch("app.institucional.service.obter_url_publica")
    def test_upload_banner_com_warning_resolucao(
        self, mock_url, mock_remover, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "banners/123.png"
        mock_url.return_value = "http://localhost:9000/institucional/banners/123.png"
        service_mocked.repository.buscar_configuracoes.return_value = _config_com(
            "arquivo_banner", ""
        )

        buffer_img = _gerar_imagem_bytes(800, 400, cor="red")
        file_mock = UploadFile(filename="banner.png", file=buffer_img)

        url, warning = service_mocked.upload_midia(file_mock, "banner")

        assert url == "http://localhost:9000/institucional/banners/123.png"
        assert warning is not None
        assert "abaixo da recomendada" in warning

    @patch("app.institucional.service.salvar_arquivo")
    @patch("app.institucional.service.obter_url_publica")
    def test_upload_banner_imagem_corrompida_trata_excecao_pillow(
        self, mock_url, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "banners/corrompido.png"
        mock_url.return_value = "http://localhost:9000/banners/corrompido.png"
        service_mocked.repository.buscar_configuracoes.return_value = _config_com(
            "arquivo_banner", ""
        )

        conteudo_corrompido = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"0" * 100
        file_mock = UploadFile(filename="banner.png", file=io.BytesIO(conteudo_corrompido))

        url, warning = service_mocked.upload_midia(file_mock, "banner")

        assert url == "http://localhost:9000/banners/corrompido.png"
        assert warning is None

    @patch("app.institucional.service.salvar_arquivo")
    @patch("app.institucional.service.remover_arquivo")
    @patch("app.institucional.service.obter_url_publica")
    def test_upload_sobre_com_warning_resolucao(
        self, mock_url, mock_remover, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "sobre/123.png"
        mock_url.return_value = "http://localhost:9000/institucional/sobre/123.png"
        service_mocked.repository.buscar_configuracoes.return_value = _config_com(
            "arquivo_sobre", ""
        )

        buffer_img = _gerar_imagem_bytes(400, 300, cor="blue")
        file_mock = UploadFile(filename="sobre.png", file=buffer_img)

        url, warning = service_mocked.upload_midia(file_mock, "sobre")

        assert url == "http://localhost:9000/institucional/sobre/123.png"
        assert warning is not None
        assert "800x600px" in warning

    @patch("app.institucional.service.salvar_arquivo")
    @patch("app.institucional.service.remover_arquivo")
    @patch("app.institucional.service.obter_url_publica")
    def test_upload_sobre_sucesso_com_remocao_antiga(
        self, mock_url, mock_remover, mock_salvar, service_mocked
    ):
        mock_salvar.return_value = "sobre/novo.png"
        mock_url.return_value = "http://localhost:9000/institucional/sobre/novo.png"
        service_mocked.repository.buscar_configuracoes.return_value = _config_com(
            "arquivo_sobre", "sobre/antigo.png"
        )

        buffer_img = _gerar_imagem_bytes(800, 600, cor="green")
        file_mock = UploadFile(filename="sobre.png", file=buffer_img)

        url, warning = service_mocked.upload_midia(file_mock, "sobre")

        assert url == "http://localhost:9000/institucional/sobre/novo.png"
        assert warning is None
        mock_remover.assert_called_once_with("sobre/antigo.png")
        service_mocked.repository.atualizar_configuracoes.assert_called_once_with(
            {"imagem_sobre_escritorio": 5}
        )
