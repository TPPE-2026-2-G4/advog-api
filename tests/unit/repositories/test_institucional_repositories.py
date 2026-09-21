import pytest

from app.models.institucional import Institucional
from app.repositories.institucional import InstitucionalNaoEncontradoError, InstitucionalRepository


def test_buscar_configuracoes_sucesso(db_session):
    repository = InstitucionalRepository(db_session)
    config = Institucional(
        institucional_id=1,
        nome_escritorio="Escritório Teste",
        imagem_sobre="sobre/foto_inicial.jpg",
        texto_adicional_sobre="10 anos de atuação",
    )
    db_session.add(config)
    db_session.commit()

    resultado = repository.buscar_configuracoes()
    assert resultado.institucional_id == 1
    assert resultado.nome_escritorio == "Escritório Teste"
    assert resultado.imagem_sobre == "sobre/foto_inicial.jpg"
    assert resultado.texto_adicional_sobre == "10 anos de atuação"


def test_buscar_configuracoes_inexistente_lanca_excesao(db_session):
    repository = InstitucionalRepository(db_session)
    with pytest.raises(InstitucionalNaoEncontradoError):
        repository.buscar_configuracoes()


def test_atualizar_configuracoes_sucesso(db_session):
    repository = InstitucionalRepository(db_session)
    config = Institucional(institucional_id=1, nome_escritorio="Antigo")
    db_session.add(config)
    db_session.commit()

    atualizado = repository.atualizar_configuracoes(
        {
            "nome_escritorio": "Novo",
            "imagem_sobre": "sobre/imagem.png",
            "texto_adicional_sobre": "Mais de 500 casos resolvidos",
        }
    )
    assert atualizado.nome_escritorio == "Novo"
    assert atualizado.imagem_sobre == "sobre/imagem.png"
    assert atualizado.texto_adicional_sobre == "Mais de 500 casos resolvidos"
