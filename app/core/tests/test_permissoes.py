import pytest

from app.cargo.schema import PermissaoBase
from app.core import permissoes
from app.core.dependencies import exigir_permissao

CAMPOS = set(PermissaoBase.model_fields)
ACESSOS = {nome: valor for nome, valor in vars(permissoes).items() if nome.startswith("ACESSO_")}


def test_todas_as_permissoes_implicadas_existem_no_schema():
    for gerenciar, visualizar in permissoes.PERMISSOES_IMPLICADAS.items():
        assert {gerenciar, visualizar} <= CAMPOS


@pytest.mark.parametrize("nome", ACESSOS)
def test_acessos_compartilhados_usam_permissoes_existentes(nome):
    assert set(ACESSOS[nome]) <= CAMPOS
    assert len(ACESSOS[nome]) >= 2


def test_exigir_permissao_rejeita_nome_inexistente():
    with pytest.raises(ValueError, match="inexistente"):
        exigir_permissao("gerenciar_processo")
