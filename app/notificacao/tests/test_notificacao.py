import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.dependencies import obter_funcionario_atual
from app.funcionario.model import Funcionario
from app.notificacao.controller import (
    _extrair_funcionario_id,
    _traduzir_erro,
    get_notificacao_service,
)
from app.notificacao.model import Notificacao, TipoNotificacao
from app.notificacao.repository import NotificacaoRepository
from app.notificacao.schema import (
    ContagemNaoLidasResponse,
    NotificacaoCreate,
    NotificacaoPaginatedResponse,
    NotificacaoRead,
)
from app.notificacao.service import (
    NotificacaoAcessoNegadoError,
    NotificacaoNaoEncontradaError,
    NotificacaoService,
)
from main import app

funcionario_id_PRINCIPAL = uuid.UUID("a1111111-1111-1111-1111-111111111111")
funcionario_id_SECUNDARIO = uuid.UUID("b2222222-2222-2222-2222-222222222222")

NOTIFICACAO_ID_UM = uuid.UUID("c3333333-3333-3333-3333-333333333333")
NOTIFICACAO_ID_DOIS = uuid.UUID("d4444444-4444-4444-4444-444444444444")
NOTIFICACAO_ID_TRES = uuid.UUID("e5555555-5555-5555-5555-555555555555")
NOTIFICACAO_ID_OUTRO = uuid.UUID("f6666666-6666-6666-6666-666666666666")
NOTIFICACAO_ID_INEXISTENTE = uuid.UUID("f9999999-9999-9999-9999-999999999999")


@pytest.fixture
def funcionario_autenticado() -> Funcionario:
    funcionario = Funcionario()
    funcionario.__dict__["id"] = funcionario_id_PRINCIPAL
    return funcionario


@pytest.fixture
def funcionario_terceiro_autenticado() -> Funcionario:
    funcionario = Funcionario()
    funcionario.__dict__["id"] = funcionario_id_SECUNDARIO
    return funcionario


@pytest.fixture
def notificacoes_semeadas(db_session: Any) -> list[Notificacao]:
    notificacoes = [
        Notificacao(
            id=NOTIFICACAO_ID_UM,
            funcionario_id=funcionario_id_PRINCIPAL,
            titulo="Atribuição de Atividade",
            mensagem="Você foi atribuído à atividade Elaborar Petição.",
            tipo=TipoNotificacao.ATRIBUICAO,
            lida=False,
            link_destino="/atividades/1",
            criado_em=datetime(2026, 10, 1, 10, 0, 0, tzinfo=UTC),
        ),
        Notificacao(
            id=NOTIFICACAO_ID_DOIS,
            funcionario_id=funcionario_id_PRINCIPAL,
            titulo="Vencimento Próximo",
            mensagem="A atividade expira em 24 horas.",
            tipo=TipoNotificacao.VENCIMENTO_1D,
            lida=False,
            link_destino="/atividades/2",
            criado_em=datetime(2026, 10, 2, 10, 0, 0, tzinfo=UTC),
        ),
        Notificacao(
            id=NOTIFICACAO_ID_TRES,
            funcionario_id=funcionario_id_PRINCIPAL,
            titulo="Aviso do Sistema",
            mensagem="Manutenção programada.",
            tipo=TipoNotificacao.SISTEMA,
            lida=True,
            link_destino=None,
            criado_em=datetime(2026, 10, 3, 10, 0, 0, tzinfo=UTC),
        ),
        Notificacao(
            id=NOTIFICACAO_ID_OUTRO,
            funcionario_id=funcionario_id_SECUNDARIO,
            titulo="Notificação Privada",
            mensagem="Conteúdo exclusivo.",
            tipo=TipoNotificacao.NOVO_CLIENTE,
            lida=False,
            link_destino=None,
            criado_em=datetime(2026, 10, 4, 10, 0, 0, tzinfo=UTC),
        ),
    ]
    db_session.add_all(notificacoes)
    db_session.commit()
    for notificacao in notificacoes:
        db_session.refresh(notificacao)
    return notificacoes


class TestNotificacaoSchema:
    @pytest.mark.parametrize(
        (
            "titulo",
            "mensagem",
            "tipo",
            "link_destino",
            "funcionario_id",
            "deve_ser_valido",
            "campo_com_erro",
        ),
        [
            (
                "Título Válido",
                "Mensagem válida e completa.",
                TipoNotificacao.SISTEMA,
                "/processos/1",
                funcionario_id_PRINCIPAL,
                True,
                None,
            ),
            (
                "A",
                "Mensagem simples.",
                TipoNotificacao.ATRIBUICAO,
                None,
                funcionario_id_PRINCIPAL,
                True,
                None,
            ),
            (
                "A" * 150,
                "Mensagem limite máximo.",
                TipoNotificacao.ATRASO,
                "https://app.advog.com/" + "x" * 230,
                funcionario_id_PRINCIPAL,
                True,
                None,
            ),
            (
                None,
                "Mensagem",
                TipoNotificacao.SISTEMA,
                None,
                funcionario_id_PRINCIPAL,
                False,
                "titulo",
            ),
            (
                "A" * 151,
                "Mensagem",
                TipoNotificacao.SISTEMA,
                None,
                funcionario_id_PRINCIPAL,
                False,
                "titulo",
            ),
            (
                "Título",
                "Mensagem",
                TipoNotificacao.SISTEMA,
                "https://app.advog.com/" + "x" * 235,
                funcionario_id_PRINCIPAL,
                False,
                "link_destino",
            ),
            (
                "Título",
                "Mensagem",
                "TIPO_INVALIDO",
                None,
                funcionario_id_PRINCIPAL,
                False,
                "tipo",
            ),
            (
                "Título",
                "Mensagem",
                TipoNotificacao.SISTEMA,
                None,
                "uuid_invalido",
                False,
                "funcionario_id",
            ),
        ],
    )
    def test_validar_schema_notificacao_create_limites_e_particionamento(
        self,
        titulo: Any,
        mensagem: Any,
        tipo: Any,
        link_destino: Any,
        funcionario_id: Any,
        deve_ser_valido: bool,
        campo_com_erro: str | None,
    ) -> None:
        payload = {
            "titulo": titulo,
            "mensagem": mensagem,
            "tipo": tipo,
            "link_destino": link_destino,
            "funcionario_id": funcionario_id,
        }

        if deve_ser_valido:
            instancia = NotificacaoCreate.model_validate(payload)
            assert instancia.titulo == titulo
            assert instancia.link_destino == link_destino
        else:
            with pytest.raises(ValidationError) as informacao_excecao:
                NotificacaoCreate.model_validate(payload)
            campos_com_erro = [erro["loc"][0] for erro in informacao_excecao.value.errors()]
            assert campo_com_erro in campos_com_erro

    def test_validar_schema_notificacao_read(self) -> None:
        dados = {
            "id": NOTIFICACAO_ID_UM,
            "funcionario_id": funcionario_id_PRINCIPAL,
            "titulo": "Notificação Lida",
            "mensagem": "Conteúdo lido.",
            "tipo": TipoNotificacao.SISTEMA,
            "lida": True,
            "link_destino": None,
            "criado_em": datetime.now(UTC),
        }
        instancia = NotificacaoRead.model_validate(dados)
        assert instancia.id == NOTIFICACAO_ID_UM
        assert instancia.lida is True

    def test_validar_schema_notificacao_paginated_response(self) -> None:
        dados_notificacao = {
            "id": NOTIFICACAO_ID_UM,
            "funcionario_id": funcionario_id_PRINCIPAL,
            "titulo": "Notificação",
            "mensagem": "Mensagem",
            "tipo": TipoNotificacao.SISTEMA,
            "lida": False,
            "link_destino": None,
            "criado_em": datetime.now(UTC),
        }
        resposta_paginada = NotificacaoPaginatedResponse(
            items=[NotificacaoRead.model_validate(dados_notificacao)],
            total=1,
            nao_lidas_count=1,
            page=1,
            size=10,
        )
        assert resposta_paginada.total == 1
        assert len(resposta_paginada.items) == 1

    def test_validar_schema_contagem_nao_lidas(self) -> None:
        resposta = ContagemNaoLidasResponse(total_nao_lidas=42)
        assert resposta.total_nao_lidas == 42


class TestNotificacaoRepository:
    def test_buscar_por_id_existente_e_inexistente(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
    ) -> None:
        repositorio = NotificacaoRepository(db_session)

        notificacao_encontrada = repositorio.buscar_por_id(NOTIFICACAO_ID_UM)
        notificacao_inexistente = repositorio.buscar_por_id(NOTIFICACAO_ID_INEXISTENTE)

        assert notificacao_encontrada is not None
        assert notificacao_encontrada.id == NOTIFICACAO_ID_UM
        assert notificacao_inexistente is None

    @pytest.mark.parametrize(
        (
            "apenas_nao_lidas",
            "tipo_filtro",
            "limite",
            "offset",
            "quantidade_esperada",
        ),
        [
            (False, None, 50, 0, 3),
            (True, None, 50, 0, 2),
            (False, TipoNotificacao.SISTEMA, 50, 0, 1),
            (True, TipoNotificacao.SISTEMA, 50, 0, 0),
            (False, None, 1, 0, 1),
            (False, None, 50, 2, 1),
        ],
    )
    def test_listar_por_usuario_combinacoes_e_filtros(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
        apenas_nao_lidas: bool,
        tipo_filtro: TipoNotificacao | None,
        limite: int,
        offset: int,
        quantidade_esperada: int,
    ) -> None:
        repositorio = NotificacaoRepository(db_session)

        resultado = repositorio.listar_por_usuario(
            funcionario_id=funcionario_id_PRINCIPAL,
            apenas_nao_lidas=apenas_nao_lidas,
            tipo=tipo_filtro,
            limite=limite,
            offset=offset,
        )

        assert len(resultado) == quantidade_esperada

    def test_contar_nao_lidas(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
    ) -> None:
        repositorio = NotificacaoRepository(db_session)

        contagem_principal = repositorio.contar_nao_lidas(funcionario_id_PRINCIPAL)
        contagem_secundario = repositorio.contar_nao_lidas(funcionario_id_SECUNDARIO)
        contagem_usuario_sem_notificacao = repositorio.contar_nao_lidas(uuid.uuid4())

        assert contagem_principal == 2
        assert contagem_secundario == 1
        assert contagem_usuario_sem_notificacao == 0

    def test_criar_notificacao(
        self,
        db_session: Any,
    ) -> None:
        repositorio = NotificacaoRepository(db_session)
        nova_notificacao = Notificacao(
            id=uuid.uuid4(),
            funcionario_id=funcionario_id_PRINCIPAL,
            titulo="Nova Notificação Criada",
            mensagem="Mensagem de teste.",
            tipo=TipoNotificacao.SISTEMA,
            lida=False,
        )

        notificacao_salva = repositorio.criar(nova_notificacao)

        assert notificacao_salva.id == nova_notificacao.id
        assert repositorio.buscar_por_id(nova_notificacao.id) is not None

    def test_marcar_como_lida(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
    ) -> None:
        repositorio = NotificacaoRepository(db_session)

        sucesso = repositorio.marcar_como_lida(NOTIFICACAO_ID_UM, funcionario_id_PRINCIPAL)
        falha_usuario = repositorio.marcar_como_lida(NOTIFICACAO_ID_UM, funcionario_id_SECUNDARIO)

        assert sucesso is True
        assert falha_usuario is False

    def test_marcar_todas_como_lidas(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
    ) -> None:
        repositorio = NotificacaoRepository(db_session)

        alteradas = repositorio.marcar_todas_como_lidas(funcionario_id_PRINCIPAL)
        alteradas_novamente = repositorio.marcar_todas_como_lidas(funcionario_id_PRINCIPAL)

        assert alteradas == 2
        assert alteradas_novamente == 0


class TestNotificacaoService:
    def test_listar_notificacoes_servico(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
    ) -> None:
        servico = NotificacaoService(db_session)

        resultado = servico.listar_notificacoes(funcionario_id_PRINCIPAL)

        assert len(resultado) == 3
        assert all(isinstance(item, NotificacaoRead) for item in resultado)

    def test_obter_contagem_nao_lidas_servico(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
    ) -> None:
        servico = NotificacaoService(db_session)

        resposta = servico.obter_contagem_nao_lidas(funcionario_id_PRINCIPAL)

        assert isinstance(resposta, ContagemNaoLidasResponse)
        assert resposta.total_nao_lidas == 2

    def test_criar_notificacao_servico(
        self,
        db_session: Any,
    ) -> None:
        servico = NotificacaoService(db_session)
        dados = NotificacaoCreate(
            titulo="Nova Notificação",
            mensagem="Mensagem enviada pelo serviço.",
            tipo=TipoNotificacao.ATRIBUICAO,
            funcionario_id=funcionario_id_PRINCIPAL,
        )

        resultado = servico.criar_notificacao(dados)

        assert resultado.titulo == "Nova Notificação"
        assert resultado.funcionario_id == funcionario_id_PRINCIPAL

    @pytest.mark.parametrize(
        ("notificacao_id", "funcionario_id", "excecao_esperada"),
        [
            (NOTIFICACAO_ID_UM, funcionario_id_PRINCIPAL, None),
            (
                NOTIFICACAO_ID_INEXISTENTE,
                funcionario_id_PRINCIPAL,
                NotificacaoNaoEncontradaError,
            ),
            (
                NOTIFICACAO_ID_UM,
                funcionario_id_SECUNDARIO,
                NotificacaoAcessoNegadoError,
            ),
        ],
    )
    def test_marcar_como_lida_caminhos_basicos(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
        notificacao_id: uuid.UUID,
        funcionario_id: uuid.UUID,
        excecao_esperada: type[Exception] | None,
    ) -> None:
        servico = NotificacaoService(db_session)

        if excecao_esperada is None:
            resultado = servico.marcar_como_lida(notificacao_id, funcionario_id)
            assert resultado.lida is True
        else:
            with pytest.raises(excecao_esperada):
                servico.marcar_como_lida(notificacao_id, funcionario_id)

    def test_marcar_todas_como_lidas_servico(
        self,
        db_session: Any,
        notificacoes_semeadas: list[Notificacao],
    ) -> None:
        servico = NotificacaoService(db_session)

        total_alterado = servico.marcar_todas_como_lidas(funcionario_id_PRINCIPAL)

        assert total_alterado == 2


class TestNotificacaoController:
    def test_extrair_funcionario_id_sucesso_e_falha(self) -> None:
        usuario_valido_com_id = Funcionario()
        usuario_valido_com_id.__dict__["id"] = funcionario_id_PRINCIPAL

        usuario_valido_com_funcionario_id = Funcionario()
        usuario_valido_com_funcionario_id.__dict__["funcionario_id"] = funcionario_id_PRINCIPAL

        usuario_invalido_sem_uuid = Funcionario()
        usuario_invalido_sem_uuid.__dict__["funcionario_id"] = 123

        assert _extrair_funcionario_id(usuario_valido_com_id) == funcionario_id_PRINCIPAL
        assert (
            _extrair_funcionario_id(usuario_valido_com_funcionario_id) == funcionario_id_PRINCIPAL
        )

        with pytest.raises(HTTPException) as excecao_info:
            _extrair_funcionario_id(usuario_invalido_sem_uuid)
        assert excecao_info.value.status_code == 401

    @pytest.mark.parametrize(
        ("excecao_origem", "status_esperado"),
        [
            (NotificacaoNaoEncontradaError("Não encontrada"), 404),
            (NotificacaoAcessoNegadoError("Acesso negado"), 403),
            (ValueError("Erro genérico"), 422),
        ],
    )
    def test_traduzir_erro_mapeamento_status(
        self,
        excecao_origem: ValueError,
        status_esperado: int,
    ) -> None:
        http_excecao = _traduzir_erro(excecao_origem)
        assert http_excecao.status_code == status_esperado

    def test_listar_notificacoes_endpoint(
        self,
        client: TestClient,
        notificacoes_semeadas: list[Notificacao],
        funcionario_autenticado: Funcionario,
    ) -> None:

        app.dependency_overrides[obter_funcionario_atual] = lambda: funcionario_autenticado

        resposta = client.get("/notificacoes")

        app.dependency_overrides.clear()

        assert resposta.status_code == 200
        dados = resposta.json()
        assert len(dados) == 3

    @pytest.mark.parametrize(
        ("limite", "offset", "status_esperado"),
        [
            (1, 0, 200),
            (50, 0, 200),
            (100, 0, 200),
            (0, 0, 422),
            (101, 0, 422),
            (50, -1, 422),
        ],
    )
    def test_listar_notificacoes_paginacao_bva(
        self,
        client: TestClient,
        notificacoes_semeadas: list[Notificacao],
        funcionario_autenticado: Funcionario,
        limite: int,
        offset: int,
        status_esperado: int,
    ) -> None:

        app.dependency_overrides[obter_funcionario_atual] = lambda: funcionario_autenticado

        resposta = client.get(f"/notificacoes?limite={limite}&offset={offset}")

        app.dependency_overrides.clear()

        assert resposta.status_code == status_esperado

    def test_obter_contagem_nao_lidas_endpoint(
        self,
        client: TestClient,
        notificacoes_semeadas: list[Notificacao],
        funcionario_autenticado: Funcionario,
    ) -> None:

        app.dependency_overrides[obter_funcionario_atual] = lambda: funcionario_autenticado

        resposta = client.get("/notificacoes/nao-lidas/contagem")

        app.dependency_overrides.clear()

        assert resposta.status_code == 200
        assert resposta.json()["total_nao_lidas"] == 2

    def test_criar_notificacao_endpoint_sucesso(
        self,
        client: TestClient,
        funcionario_autenticado: Funcionario,
    ) -> None:

        app.dependency_overrides[obter_funcionario_atual] = lambda: funcionario_autenticado

        payload = {
            "titulo": "Nova Notificação Endpoint",
            "mensagem": "Criada com sucesso via HTTP.",
            "tipo": "NOVO_CLIENTE",
            "funcionario_id": str(funcionario_id_PRINCIPAL),
        }

        resposta = client.post("/notificacoes", json=payload)

        app.dependency_overrides.clear()

        assert resposta.status_code == 201
        assert resposta.json()["titulo"] == "Nova Notificação Endpoint"

    def test_marcar_todas_como_lidas_endpoint(
        self,
        client: TestClient,
        notificacoes_semeadas: list[Notificacao],
        funcionario_autenticado: Funcionario,
    ) -> None:

        app.dependency_overrides[obter_funcionario_atual] = lambda: funcionario_autenticado

        resposta = client.patch("/notificacoes/marcar-todas-lidas")

        app.dependency_overrides.clear()

        assert resposta.status_code == 200
        assert resposta.json()["alteradas"] == 2

    @pytest.mark.parametrize(
        ("notificacao_id_path", "funcionario_mock", "status_esperado"),
        [
            (str(NOTIFICACAO_ID_UM), "funcionario_autenticado", 200),
            (str(NOTIFICACAO_ID_INEXISTENTE), "funcionario_autenticado", 404),
            (str(NOTIFICACAO_ID_UM), "funcionario_terceiro_autenticado", 403),
            ("id_invalido", "funcionario_autenticado", 422),
        ],
    )
    def test_marcar_como_lida_endpoint_matriz_respostas(
        self,
        client: TestClient,
        notificacoes_semeadas: list[Notificacao],
        request: pytest.FixtureRequest,
        notificacao_id_path: str,
        funcionario_mock: str,
        status_esperado: int,
    ) -> None:

        funcionario: Funcionario = request.getfixturevalue(funcionario_mock)
        app.dependency_overrides[obter_funcionario_atual] = lambda: funcionario

        resposta = client.patch(f"/notificacoes/{notificacao_id_path}/lida")

        app.dependency_overrides.clear()

        assert resposta.status_code == status_esperado

    def test_criar_notificacao_traduz_erro_de_valor_controller(
        self,
        client: TestClient,
        funcionario_autenticado: Funcionario,
    ) -> None:

        app.dependency_overrides[obter_funcionario_atual] = lambda: funcionario_autenticado

        mock_service = MagicMock()
        mock_service.criar_notificacao.side_effect = ValueError("Dados inválidos")
        app.dependency_overrides[get_notificacao_service] = lambda: mock_service

        resposta = client.post(
            "/notificacoes",
            json={
                "titulo": "Nova notificação",
                "mensagem": "Mensagem de teste",
                "tipo": "SISTEMA",
                "funcionario_id": str(funcionario_id_PRINCIPAL),
            },
        )

        app.dependency_overrides.clear()

        assert resposta.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert resposta.json()["detail"] == "Dados inválidos"
