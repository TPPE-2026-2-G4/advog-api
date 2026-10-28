from app.arquivo.model import Arquivo
from app.arquivo.repository import LINK_ARQUIVO_PADRAO, ArquivoRepository


def _novo_arquivo(**campos) -> Arquivo:
    return Arquivo(
        nome_arquivo="peticao.pdf",
        tipo_mime="application/pdf",
        tamanho_bytes=2048,
        bucket_link="processos/1/peticao.pdf",
        **campos,
    )


def test_adicionar_buscar_e_deletar(db_session):
    repository = ArquivoRepository(db_session)

    salvo = repository.adicionar(_novo_arquivo())

    assert salvo.arquivo_id is not None
    assert salvo.origem == "manual"
    assert salvo.data_upload is not None
    assert salvo.funcionario_id is None
    assert repository.buscar_por_id(salvo.arquivo_id) == salvo

    repository.deletar(salvo)

    assert repository.buscar_por_id(salvo.arquivo_id) is None


def test_obter_padrao_cria_uma_unica_vez(db_session):
    repository = ArquivoRepository(db_session)

    primeiro = repository.obter_padrao()
    segundo = repository.obter_padrao()
    db_session.commit()

    assert primeiro.arquivo_id == segundo.arquivo_id
    assert primeiro.bucket_link == LINK_ARQUIVO_PADRAO
    assert primeiro.tamanho_bytes == 0
    assert primeiro.origem == "sistema"
    assert db_session.query(Arquivo).count() == 1
