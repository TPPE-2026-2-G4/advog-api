import pytest
from sqlalchemy import create_engine, text

from app.config.database import get_db, validar_database_url


def test_validar_database_url_producao_sem_url_lanca_erro():
    with pytest.raises(RuntimeError, match="DATABASE_URL é obrigatória no ambiente de produção"):
        validar_database_url(None, "production")

    with pytest.raises(RuntimeError, match="DATABASE_URL é obrigatória no ambiente de produção"):
        validar_database_url("   ", "production")


def test_validar_database_url_producao_sqlite_lanca_erro():
    with pytest.raises(
        RuntimeError, match="Fallback para SQLite não é permitido no ambiente de produção"
    ):
        validar_database_url("sqlite:///./advog_db.sqlite", "production")

    with pytest.raises(
        RuntimeError, match="Fallback para SQLite não é permitido no ambiente de produção"
    ):
        validar_database_url("sqlite:///:memory:", "production")


def test_validar_database_url_producao_valida_sucesso():
    url_postgres = "postgresql://postgres.abc:pass@aws-0-us-east-2.pooler.supabase.com:5432/postgres?sslmode=require"
    resultado = validar_database_url(url_postgres, "production")
    assert resultado == url_postgres


def test_validar_database_url_converte_postgres_para_postgresql():
    url_legada = "postgres://postgres.abc:pass@aws-0-us-east-2.pooler.supabase.com:5432/postgres?sslmode=require"
    resultado = validar_database_url(url_legada, "production")
    assert resultado.startswith("postgresql://")


def test_validar_database_url_desenvolvimento_fallback_sqlite():
    resultado = validar_database_url(None, "development")
    assert resultado == "sqlite:///./advog_db.sqlite"

    resultado_vazio = validar_database_url("  ", "development")
    assert resultado_vazio == "sqlite:///./advog_db.sqlite"


def test_validar_database_url_desenvolvimento_url_customizada():
    url_custom = "sqlite:///./custom.db"
    assert validar_database_url(url_custom, "development") == url_custom


def test_get_db_yields_e_fecha_sessao():
    generator = get_db()
    sessao = next(generator)
    assert sessao is not None
    with pytest.raises(StopIteration):
        next(generator)


def test_banco_reconecta_automaticamente_apos_desconexao_simulada(tmp_path):
    # Cria uma engine com pool_pre_ping e parâmetros de pool em banco SQLite local
    caminho_db = tmp_path / "test_reconexao.db"
    url = f"sqlite:///{caminho_db}"
    engine = create_engine(url, pool_pre_ping=True, pool_recycle=300, pool_timeout=30)

    # Primeira consulta bem-sucedida
    with engine.connect() as conn:
        res1 = conn.execute(text("SELECT 1")).scalar()
        assert res1 == 1

    # Simula perda de conexão (como queda de conexão pelo pooler) fechando o DBAPI subjacente
    conn_morta = engine.connect()
    raw_conn = conn_morta.connection.dbapi_connection
    raw_conn.close()
    conn_morta.close()

    # Com pool_pre_ping=True, a engine detecta a conexão morta, descarta e reconecta graciosamente
    with engine.connect() as conn2:
        res2 = conn2.execute(text("SELECT 1")).scalar()
        assert res2 == 1


def _engine_postgres_falso(colunas: list[dict], tem_tabela: bool = True):
    from unittest.mock import MagicMock

    engine = MagicMock()
    engine.dialect.name = "postgresql"
    inspetor = MagicMock()
    inspetor.has_table.return_value = tem_tabela
    inspetor.get_columns.return_value = colunas
    return engine, inspetor


def test_tornar_colunas_processo_opcionais_remove_not_null_no_postgres():
    from unittest.mock import patch

    from app.config.database import _tornar_colunas_processo_opcionais

    engine, inspetor = _engine_postgres_falso(
        [
            {"name": "descricao", "nullable": False},
            {"name": "funcionario_id", "nullable": False},
        ]
    )

    with patch("app.config.database.inspect", return_value=inspetor):
        _tornar_colunas_processo_opcionais(engine)

    comandos = [
        str(chamada.args[0])
        for chamada in engine.begin.return_value.__enter__.return_value.execute.call_args_list
    ]
    assert comandos == [
        "ALTER TABLE processos ALTER COLUMN descricao DROP NOT NULL",
        "ALTER TABLE processos ALTER COLUMN funcionario_id DROP NOT NULL",
    ]


def test_tornar_colunas_processo_opcionais_ignora_colunas_ja_opcionais():
    from unittest.mock import patch

    from app.config.database import _tornar_colunas_processo_opcionais

    engine, inspetor = _engine_postgres_falso(
        [
            {"name": "descricao", "nullable": True},
            {"name": "funcionario_id", "nullable": True},
        ]
    )

    with patch("app.config.database.inspect", return_value=inspetor):
        _tornar_colunas_processo_opcionais(engine)

    engine.begin.assert_not_called()


def test_tornar_colunas_processo_opcionais_ignora_sqlite_e_tabela_ausente():
    from unittest.mock import MagicMock, patch

    from app.config.database import _tornar_colunas_processo_opcionais

    sqlite = MagicMock()
    sqlite.dialect.name = "sqlite"
    _tornar_colunas_processo_opcionais(sqlite)
    sqlite.begin.assert_not_called()

    engine, inspetor = _engine_postgres_falso([], tem_tabela=False)
    with patch("app.config.database.inspect", return_value=inspetor):
        _tornar_colunas_processo_opcionais(engine)
    engine.begin.assert_not_called()


def test_tornar_colunas_processo_opcionais_nao_propaga_erros():
    from unittest.mock import patch

    from app.config.database import _tornar_colunas_processo_opcionais

    engine, _ = _engine_postgres_falso([])

    with patch("app.config.database.inspect", side_effect=RuntimeError("falha")):
        _tornar_colunas_processo_opcionais(engine)
