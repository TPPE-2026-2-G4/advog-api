import pytest

from app.arquivo.model import Arquivo
from app.institucional.model import Institucional
from app.institucional.repository import InstitucionalNaoEncontradoError, InstitucionalRepository


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
