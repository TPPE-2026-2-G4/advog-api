"""Regras de permissão compartilhadas entre os módulos.

Tudo que acopla um módulo a outro fica aqui, num só lugar. Os controllers usam
as constantes abaixo em vez de repetir listas de permissões.
"""

# Quem gerencia um recurso sempre precisa conseguir visualizá-lo.
# Vale na checagem (core/dependencies.py) e ao gravar o cargo (cargo/schema.py).
PERMISSOES_IMPLICADAS: dict[str, str] = {
    "gerenciar_processos": "visualizar_processos",
    "gerenciar_atividades": "visualizar_atividades",
    "gerenciar_financeiro": "visualizar_financeiro",
    "gerenciar_clientes": "visualizar_clientes",
    "gerenciar_equipe": "visualizar_equipe",
}

# Acessos que uma tela precisa de OUTRO módulo para funcionar. Cada constante lista
# as permissões que liberam a rota (basta ter uma). A primeira é a do módulo dono.

# Tela de processos: formulário e tabela mostram os clientes.
ACESSO_LISTA_CLIENTES = ("visualizar_clientes", "visualizar_processos")

# Tela de atividades: o formulário vincula a atividade a um processo.
ACESSO_LISTA_PROCESSOS = ("visualizar_processos", "visualizar_atividades")

# Tela de equipe: cargos são gerenciados junto com os funcionários.
ACESSO_GERENCIAR_CARGOS = ("configuracoes_sistema", "gerenciar_equipe")


CARGOS_ADMINISTRADOR = ("administrador", "admin")


def eh_administrador(funcionario) -> bool:
    """Administrador: cargo "Administrador"/"Admin" ou quem gerencia a equipe.

    É quem enxerga o escritório inteiro (e, por isso, recebe as notificações de tudo).
    """
    cargo = getattr(funcionario, "cargo", None)
    if cargo is None:
        return False
    nome_cargo = (getattr(cargo, "nome_cargo", "") or "").strip().lower()
    permissoes = getattr(cargo, "permissao", None) or {}
    return nome_cargo in CARGOS_ADMINISTRADOR or bool(permissoes.get("gerenciar_equipe", False))


def pode_visualizar_financeiro(funcionario) -> bool:
    """Quem enxerga o financeiro: administradores e cargos com visualizar/gerenciar financeiro."""
    if eh_administrador(funcionario):
        return True
    cargo = getattr(funcionario, "cargo", None)
    permissoes = getattr(cargo, "permissao", None) or {}
    return bool(
        permissoes.get("visualizar_financeiro", False)
        or permissoes.get("gerenciar_financeiro", False)
    )
