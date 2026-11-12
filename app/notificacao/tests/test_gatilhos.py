"""Quem é notificado, quando e com qual antecedência (eventos e alertas automáticos)."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.atividade.model import Atividade
from app.atividade.schema import AtividadeCreate, AtividadeUpdate
from app.atividade.service import AtividadeService
from app.cargo.model import Cargo
from app.cliente.model import Cliente
from app.cliente.schema import ClienteCreate
from app.cliente.service import ClienteService
from app.core.permissoes import eh_administrador, pode_visualizar_financeiro
from app.funcionario.model import Funcionario, StatusFuncionario
from app.lancamento.model import Lancamento, StatusLancamento, TipoLancamento
from app.notificacao.alertas import AlertasService, executar_alertas, fase_do_prazo
from app.notificacao.eventos import NotificacaoEventos
from app.notificacao.model import Notificacao, TipoNotificacao
from app.processo.model import Processo, StatusProcesso
from app.processo.schema import ProcessoCreate, ProcessoUpdate
from app.processo.service import ProcessoService

HOJE = date(2026, 11, 12)


def _funcionario(db, cargo, nome, arquivo, status=StatusFuncionario.ATIVO, **extra):
    funcionario = Funcionario(
        nome=nome,
        email=f"{nome.lower().replace(' ', '.')}@teste.com",
        status=status,
        cargo_id=cargo.cargo_id,
        foto_perfil=arquivo.arquivo_id,
        **extra,
    )
    db.add(funcionario)
    db.commit()
    db.refresh(funcionario)
    return funcionario


@pytest.fixture
def equipe(db_session, arquivo_padrao, cargo_admin, cargo_padrao):
    """2 administradores, 2 usuários comuns, 2 do financeiro, 1 inativo e 1 pendente."""
    cargo_socio = Cargo(nome_cargo="Sócio", permissao={"gerenciar_equipe": True})
    cargo_leitura = Cargo(nome_cargo="Financeiro", permissao={"visualizar_financeiro": True})
    cargo_gestao = Cargo(nome_cargo="Contador", permissao={"gerenciar_financeiro": True})
    db_session.add_all([cargo_socio, cargo_leitura, cargo_gestao])
    db_session.commit()
    return SimpleNamespace(
        admin=_funcionario(db_session, cargo_admin, "Admin", arquivo_padrao),
        socio=_funcionario(db_session, cargo_socio, "Socio", arquivo_padrao),
        ana=_funcionario(db_session, cargo_padrao, "Ana", arquivo_padrao),
        bruno=_funcionario(db_session, cargo_padrao, "Bruno", arquivo_padrao),
        financeiro=_funcionario(db_session, cargo_leitura, "Financeiro", arquivo_padrao),
        contador=_funcionario(db_session, cargo_gestao, "Contador", arquivo_padrao),
        inativo=_funcionario(
            db_session, cargo_admin, "Inativo", arquivo_padrao, StatusFuncionario.INATIVO
        ),
        pendente=_funcionario(
            db_session, cargo_padrao, "Pendente", arquivo_padrao, StatusFuncionario.PENDENTE
        ),
    )


def _notificacoes(db, funcionario=None, tipo=None):
    consulta = db.query(Notificacao)
    if funcionario is not None:
        consulta = consulta.filter(Notificacao.funcionario_id == funcionario.funcionario_id)
    if tipo is not None:
        consulta = consulta.filter(Notificacao.tipo == tipo)
    return consulta.all()


def _quem_recebeu(db, **filtros):
    return {n.funcionario_id for n in _notificacoes(db, **filtros)}


def _ids(*funcionarios):
    return {f.funcionario_id for f in funcionarios}


def _processo(db, cnj="1", titulo="Caso", responsavel=None, **extra):
    campos = {
        "cnj": cnj,
        "titulo": titulo,
        "status": StatusProcesso.ATIVO,
        "tribunal": "TJDFT",
        "area": "Civil",
        "data_inicio": datetime(2026, 11, 11),
        "data_prazo": datetime(2027, 6, 1),
        "cliente_id": 1,
        "funcionario_id": responsavel.funcionario_id if responsavel else None,
    }
    campos.update(extra)
    processo = Processo(**campos)
    db.add(processo)
    db.commit()
    db.refresh(processo)
    return processo


class TestAdministrador:
    def test_reconhece_cargo_e_permissao(self):
        assert eh_administrador(SimpleNamespace(cargo=SimpleNamespace(nome_cargo="Admin")))
        assert eh_administrador(
            SimpleNamespace(
                cargo=SimpleNamespace(nome_cargo="Sócio", permissao={"gerenciar_equipe": True})
            )
        )
        assert not eh_administrador(
            SimpleNamespace(cargo=SimpleNamespace(nome_cargo="Advogado", permissao={}))
        )
        assert not eh_administrador(SimpleNamespace(cargo=None))


class TestEventos:
    def test_novo_cliente_avisa_administradores_e_o_responsavel(self, db_session, equipe):
        cliente = Cliente(
            nome="Maria",
            telefone="1",
            email="m@x.com",
            responsavel_id=equipe.ana.funcionario_id,
            etapa_id=1,
            ultima_interacao=datetime.now(),
        )
        db_session.add(cliente)
        db_session.commit()

        NotificacaoEventos(db_session).cliente_criado(cliente)

        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio, equipe.ana)
        da_ana = _notificacoes(db_session, equipe.ana)[0]
        assert da_ana.tipo == TipoNotificacao.NOVO_CLIENTE
        assert "sob sua responsabilidade" in da_ana.titulo
        assert da_ana.link_destino == f"/clientes?clienteId={cliente.cliente_id}"
        assert "sob sua responsabilidade" not in _notificacoes(db_session, equipe.admin)[0].titulo

    def test_cliente_sem_responsavel_so_avisa_administradores(self, db_session, equipe):
        cliente = ClienteService(db_session).create_cliente(
            ClienteCreate(nome="Joana", telefone="1", email="j@x.com")
        )

        assert cliente.cliente_id
        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio)

    def test_inativos_e_pendentes_nao_recebem(self, db_session, equipe):
        ClienteService(db_session).create_cliente(
            ClienteCreate(
                nome="Joana",
                telefone="1",
                email="j@x.com",
                responsavel_id=equipe.pendente.funcionario_id,
            )
        )

        recebeu = _quem_recebeu(db_session)
        assert equipe.inativo.funcionario_id not in recebeu
        assert equipe.pendente.funcionario_id not in recebeu

    def test_quem_fez_a_acao_nao_e_avisado(self, db_session, equipe):
        cliente = Cliente(
            nome="Maria",
            telefone="1",
            email="m@x.com",
            responsavel_id=equipe.ana.funcionario_id,
            etapa_id=1,
            ultima_interacao=datetime.now(),
        )
        db_session.add(cliente)
        db_session.commit()

        NotificacaoEventos(db_session).cliente_atribuido(
            cliente, ator_id=equipe.admin.funcionario_id
        )

        assert _quem_recebeu(db_session) == _ids(equipe.socio, equipe.ana)

    def test_trocar_responsavel_do_cliente_avisa_o_novo_responsavel(self, db_session, equipe):
        service = ClienteService(db_session)
        cliente = service.create_cliente(
            ClienteCreate(
                nome="Maria",
                telefone="1",
                email="m@x.com",
                responsavel_id=equipe.ana.funcionario_id,
            )
        )
        db_session.query(Notificacao).delete()
        db_session.commit()

        dados = SimpleNamespace(
            model_dump=lambda **_: {"responsavel_id": equipe.bruno.funcionario_id}
        )
        service.update_cliente(cliente.cliente_id, dados)

        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio, equipe.bruno)
        assert _notificacoes(db_session, equipe.bruno)[0].tipo == TipoNotificacao.ATRIBUICAO

    def test_atividade_criada_e_nova_atribuicao(self, db_session, equipe, etapas_kanban_padrao):
        service = AtividadeService(db_session)
        criada = service.criar_atividade(
            AtividadeCreate(
                titulo="Revisar contrato",
                descricao="x",
                data_inicio=datetime(2026, 11, 12),
                data_prazo=datetime(2026, 12, 12),
                etapa_id=etapas_kanban_padrao[0].etapa_id,
                responsaveis_ids=[equipe.ana.funcionario_id],
            )
        )

        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio, equipe.ana)
        assert _notificacoes(db_session, equipe.ana)[0].titulo == "Nova atividade atribuída a você"
        assert equipe.bruno.funcionario_id not in _quem_recebeu(db_session)

        db_session.query(Notificacao).delete()
        db_session.commit()
        service.atualizar_atividade(
            criada.atividade_id,
            AtividadeUpdate(
                responsaveis_ids=[equipe.ana.funcionario_id, equipe.bruno.funcionario_id]
            ),
        )

        # Só quem acabou de ser designado (Bruno) e a administração; a Ana já era responsável.
        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio, equipe.bruno)

    def test_mover_atividade_de_etapa_nao_notifica(self, db_session, equipe, etapas_kanban_padrao):
        service = AtividadeService(db_session)
        criada = service.criar_atividade(
            AtividadeCreate(
                titulo="X",
                descricao="x",
                data_inicio=datetime(2026, 11, 12),
                data_prazo=datetime(2026, 12, 12),
                etapa_id=etapas_kanban_padrao[0].etapa_id,
                responsaveis_ids=[equipe.ana.funcionario_id],
            )
        )
        db_session.query(Notificacao).delete()
        db_session.commit()

        service.atualizar_atividade(
            criada.atividade_id, AtividadeUpdate(etapa_id=etapas_kanban_padrao[1].etapa_id)
        )

        assert _notificacoes(db_session) == []

    def test_processo_atribuicao_e_mudanca_de_status(self, db_session, equipe):
        service = ProcessoService(db_session)
        processo = service.criar_processo(
            ProcessoCreate(
                cnj="0000001-00.2026.8.07.0001",
                titulo="Caso A",
                tribunal="TJDFT",
                area="Civil",
                data_inicio=datetime(2026, 11, 1),
                data_prazo=datetime(2027, 1, 1),
                cliente_id=1,
                funcionario_id=equipe.ana.funcionario_id,
            )
        )
        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio, equipe.ana)
        assert _notificacoes(db_session, equipe.ana)[0].titulo == "Processo atribuído a você"

        db_session.query(Notificacao).delete()
        db_session.commit()
        service.atualizar_processo(
            processo.processo_id, ProcessoUpdate(status=StatusProcesso.CONCLUIDO)
        )

        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio, equipe.ana)
        aviso = _notificacoes(db_session, equipe.ana)[0]
        assert aviso.tipo == TipoNotificacao.STATUS_PROCESSO
        assert '"Em Análise" para "Concluído"' in aviso.mensagem

        db_session.query(Notificacao).delete()
        db_session.commit()
        service.atualizar_processo(
            processo.processo_id, ProcessoUpdate(funcionario_id=equipe.bruno.funcionario_id)
        )
        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio, equipe.bruno)

    def test_falha_ao_notificar_nao_derruba_a_operacao(self, db_session, equipe, monkeypatch):
        def quebrar(*_args, **_kwargs):
            raise RuntimeError("banco de notificações fora do ar")

        monkeypatch.setattr("app.notificacao.eventos.destinatarios", quebrar)

        cliente = ClienteService(db_session).create_cliente(
            ClienteCreate(nome="Joana", telefone="1", email="j@x.com")
        )

        assert cliente.cliente_id
        assert _notificacoes(db_session) == []


class TestFaseDoPrazo:
    @pytest.mark.parametrize(
        "dias,antecedencia,esperado",
        [
            (-3, 7, TipoNotificacao.ATRASO),
            (0, 7, TipoNotificacao.VENCIMENTO_HOJE),
            (1, 7, TipoNotificacao.VENCIMENTO_1D),
            (2, 7, TipoNotificacao.VENCIMENTO_7D),
            (7, 7, TipoNotificacao.VENCIMENTO_7D),
            (8, 7, None),
            (15, 15, TipoNotificacao.VENCIMENTO_7D),
            (16, 15, None),
            (60, 60, TipoNotificacao.VENCIMENTO_7D),
        ],
    )
    def test_fases(self, dias, antecedencia, esperado):
        assert fase_do_prazo(dias, antecedencia) == esperado


class TestFinanceiro:
    def test_reconhece_quem_ve_o_financeiro(self):
        def com(permissao, nome="Cargo"):
            return SimpleNamespace(cargo=SimpleNamespace(nome_cargo=nome, permissao=permissao))

        assert pode_visualizar_financeiro(com({"visualizar_financeiro": True}))
        assert pode_visualizar_financeiro(com({"gerenciar_financeiro": True}))
        assert pode_visualizar_financeiro(com({"gerenciar_equipe": True}))  # administração
        assert pode_visualizar_financeiro(com({}, nome="Administrador"))
        assert not pode_visualizar_financeiro(com({"visualizar_processos": True}))
        assert not pode_visualizar_financeiro(SimpleNamespace(cargo=None))

    def test_financeiro_recebe_lancamentos_mas_nao_processos_nem_atividades(
        self, db_session, equipe, etapas_kanban_padrao
    ):
        prazo = datetime.combine(HOJE, datetime.min.time())
        _processo(db_session, responsavel=equipe.ana, data_prazo=prazo)
        db_session.add(
            Lancamento(
                titulo="Honorários",
                descricao="x",
                tipo=TipoLancamento.ENTRADA,
                data_vencimento=prazo,
                valor=500,
                categoria_id=1,
            )
        )
        db_session.commit()

        AlertasService(db_session).gerar_alertas(HOJE)

        do_financeiro = _notificacoes(db_session, equipe.financeiro)
        assert [n.link_destino for n in do_financeiro] == ["/calendario"]
        assert do_financeiro[0].tipo == TipoNotificacao.VENCIMENTO_HOJE
        assert "Honorários" in do_financeiro[0].mensagem
        assert [n.link_destino for n in _notificacoes(db_session, equipe.contador)] == [
            "/calendario"
        ]
        # Quem não vê o financeiro (usuário comum) não recebe o lançamento.
        assert all(n.link_destino != "/calendario" for n in _notificacoes(db_session, equipe.bruno))

    def test_financeiro_respeita_a_antecedencia_configurada(
        self, db_session, equipe, institucional_padrao
    ):
        institucional_padrao.dias_prazo_proximo = 7
        db_session.commit()
        db_session.add(
            Lancamento(
                titulo="Aluguel",
                descricao="x",
                tipo=TipoLancamento.SAIDA,
                data_vencimento=datetime.combine(HOJE + timedelta(days=10), datetime.min.time()),
                valor=900,
                categoria_id=1,
            )
        )
        db_session.commit()
        service = AlertasService(db_session)

        service.gerar_alertas(HOJE)
        assert _notificacoes(db_session, equipe.financeiro) == []

        service.gerar_alertas(HOJE + timedelta(days=4))  # faltam 6 dias: entrou na janela de 7
        aviso = _notificacoes(db_session, equipe.financeiro)[0]
        assert aviso.tipo == TipoNotificacao.VENCIMENTO_7D
        assert "a pagar" in aviso.titulo.lower()


class TestAlertas:
    def test_antecedencia_segue_a_configuracao_do_escritorio(
        self, db_session, equipe, institucional_padrao
    ):
        institucional_padrao.dias_prazo_proximo = 7
        db_session.commit()
        processo = _processo(
            db_session,
            responsavel=equipe.ana,
            data_prazo=datetime.combine(HOJE + timedelta(days=20), datetime.min.time()),
        )

        AlertasService(db_session).gerar_alertas(HOJE)

        # Prazo em 20 dias com antecedência de 7: ainda não é hora de avisar ninguém.
        assert _notificacoes(db_session) == []

        institucional_padrao.dias_prazo_proximo = 30
        db_session.commit()
        AlertasService(db_session).gerar_alertas(HOJE)

        # Com 30 dias, avisa o responsável e a administração (e só eles).
        assert _quem_recebeu(db_session) == _ids(equipe.admin, equipe.socio, equipe.ana)
        assert str(processo.processo_id) in _notificacoes(db_session)[0].chave

    def test_sem_configuracao_usa_15_dias(self, db_session, equipe):
        prazo = datetime.combine(HOJE + timedelta(days=15), datetime.min.time())
        _processo(db_session, cnj="1", responsavel=equipe.ana, data_prazo=prazo)
        _processo(
            db_session,
            cnj="2",
            responsavel=equipe.ana,
            data_prazo=datetime.combine(HOJE + timedelta(days=16), datetime.min.time()),
        )

        AlertasService(db_session).gerar_alertas(HOJE)

        mensagens = [n.mensagem for n in _notificacoes(db_session, equipe.ana)]
        assert len(mensagens) == 1 and "processo 1 " in mensagens[0]

    def test_usuario_comum_so_recebe_o_que_e_dele(self, db_session, equipe):
        prazo = datetime.combine(HOJE + timedelta(days=3), datetime.min.time())
        _processo(db_session, cnj="1", responsavel=equipe.ana, data_prazo=prazo)
        _processo(db_session, cnj="2", responsavel=equipe.bruno, data_prazo=prazo)

        AlertasService(db_session).gerar_alertas(HOJE)

        da_ana = _notificacoes(db_session, equipe.ana)
        do_bruno = _notificacoes(db_session, equipe.bruno)
        assert len(da_ana) == 1 and "processo 1 " in da_ana[0].mensagem
        assert len(do_bruno) == 1 and "processo 2 " in do_bruno[0].mensagem
        assert len(_notificacoes(db_session, equipe.admin)) == 2  # administrador vê tudo
        assert len(_notificacoes(db_session, equipe.inativo)) == 0

    def test_processo_critico_segue_os_dias_configurados(
        self, db_session, equipe, institucional_padrao
    ):
        institucional_padrao.dias_processo_critico = 30
        db_session.commit()
        _processo(
            db_session,
            responsavel=equipe.ana,
            data_inicio=datetime.combine(HOJE - timedelta(days=20), datetime.min.time()),
        )

        AlertasService(db_session).gerar_alertas(HOJE)
        assert _quem_recebeu(db_session, tipo=TipoNotificacao.SISTEMA) == set()

        institucional_padrao.dias_processo_critico = 10
        db_session.commit()
        AlertasService(db_session).gerar_alertas(HOJE)

        criticos = _notificacoes(db_session, tipo=TipoNotificacao.SISTEMA)
        assert {n.funcionario_id for n in criticos} == _ids(equipe.admin, equipe.socio, equipe.ana)
        assert "20 dias sem movimentação" in criticos[0].mensagem
        assert "limite configurado: 10 dias" in criticos[0].mensagem
        assert equipe.bruno.funcionario_id not in {n.funcionario_id for n in criticos}

    def test_rodar_de_novo_nao_duplica(self, db_session, equipe):
        _processo(
            db_session,
            responsavel=equipe.ana,
            data_prazo=datetime.combine(HOJE, datetime.min.time()),
        )
        service = AlertasService(db_session)

        primeira = service.gerar_alertas(HOJE)
        segunda = service.gerar_alertas(HOJE)

        assert primeira > 0
        assert segunda == 0
        assert {n.tipo for n in _notificacoes(db_session)} == {TipoNotificacao.VENCIMENTO_HOJE}

    def test_fases_geram_avisos_distintos_ao_longo_dos_dias(self, db_session, equipe):
        prazo = datetime.combine(HOJE + timedelta(days=5), datetime.min.time())
        _processo(db_session, responsavel=equipe.ana, data_prazo=prazo)
        service = AlertasService(db_session)

        service.gerar_alertas(HOJE)  # entrou na janela (15 dias)
        service.gerar_alertas(HOJE + timedelta(days=4))  # amanhã
        service.gerar_alertas(HOJE + timedelta(days=5))  # hoje
        service.gerar_alertas(HOJE + timedelta(days=6))  # atrasado

        tipos = [n.tipo for n in _notificacoes(db_session, equipe.ana)]
        assert sorted(tipos) == sorted(
            [
                TipoNotificacao.VENCIMENTO_7D,
                TipoNotificacao.VENCIMENTO_1D,
                TipoNotificacao.VENCIMENTO_HOJE,
                TipoNotificacao.ATRASO,
            ]
        )

    def test_finalizados_nao_geram_alertas(self, db_session, equipe, etapas_kanban_padrao):
        prazo = datetime.combine(HOJE, datetime.min.time())
        _processo(db_session, cnj="1", status=StatusProcesso.CONCLUIDO, data_prazo=prazo)
        db_session.add(
            Atividade(
                titulo="Pronta",
                descricao="x",
                data_inicio=prazo - timedelta(days=2),
                data_prazo=prazo,
                etapa_id=etapas_kanban_padrao[3].etapa_id,  # Finalizado
            )
        )
        db_session.add(
            Lancamento(
                titulo="Pago",
                descricao="x",
                tipo=TipoLancamento.SAIDA,
                status=StatusLancamento.REALIZADO,
                data_vencimento=prazo,
                data_pagamento=prazo,
                valor=10,
                categoria_id=1,
            )
        )
        db_session.commit()

        assert AlertasService(db_session).gerar_alertas(HOJE) == 0

    def test_atividade_vai_para_responsaveis_e_lancamento_para_administracao_e_financeiro(
        self, db_session, equipe, etapas_kanban_padrao
    ):
        prazo = datetime.combine(HOJE + timedelta(days=1), datetime.min.time())
        atividade = Atividade(
            titulo="Protocolar",
            descricao="x",
            data_inicio=prazo - timedelta(days=3),
            data_prazo=prazo,
            etapa_id=etapas_kanban_padrao[0].etapa_id,
        )
        atividade.funcionarios = [equipe.ana]
        db_session.add(atividade)
        db_session.add(
            Lancamento(
                titulo="Aluguel",
                descricao="x",
                tipo=TipoLancamento.SAIDA,
                data_vencimento=prazo,
                valor=1000,
                categoria_id=1,
            )
        )
        db_session.commit()

        AlertasService(db_session).gerar_alertas(HOJE)

        de_atividade = [n for n in _notificacoes(db_session) if n.link_destino == "/atividades"]
        de_lancamento = [n for n in _notificacoes(db_session) if n.link_destino == "/calendario"]
        assert {n.funcionario_id for n in de_atividade} == _ids(
            equipe.admin, equipe.socio, equipe.ana
        )
        # Lançamento não tem responsável: vai para a administração e para o financeiro.
        assert {n.funcionario_id for n in de_lancamento} == _ids(
            equipe.admin, equipe.socio, equipe.financeiro, equipe.contador
        )
        assert all(n.tipo == TipoNotificacao.VENCIMENTO_1D for n in de_atividade + de_lancamento)

    def test_executar_alertas_usa_a_sessao_do_banco(self, db_session, equipe):
        _processo(
            db_session,
            responsavel=equipe.ana,
            data_prazo=datetime.combine(date.today(), datetime.min.time()),
        )

        assert executar_alertas() > 0


class TestApi:
    def _cabecalho(self, token_acesso, funcionario):
        return {
            "Authorization": f"Bearer {token_acesso(funcionario.funcionario_id, funcionario.email)}"
        }

    def test_cada_usuario_so_ve_as_proprias_notificacoes(self, client, equipe, token_acesso):
        # O formulário público cria o cliente já atribuído à Ana.
        resposta = client.post(
            "/clientes/",
            json={
                "nome": "Cliente do Site",
                "telefone": "61999990000",
                "email": "site@teste.com",
                "responsavel_id": equipe.ana.funcionario_id,
            },
        )
        assert resposta.status_code == 201

        def titulos(funcionario):
            lista = client.get("/notificacoes", headers=self._cabecalho(token_acesso, funcionario))
            assert lista.status_code == 200
            return [n["titulo"] for n in lista.json()]

        assert titulos(equipe.admin) == ["Novo cliente cadastrado"]
        assert titulos(equipe.socio) == ["Novo cliente cadastrado"]
        assert titulos(equipe.ana) == ["Novo cliente sob sua responsabilidade"]
        assert titulos(equipe.bruno) == []

        contagem = client.get(
            "/notificacoes/nao-lidas/contagem", headers=self._cabecalho(token_acesso, equipe.bruno)
        )
        assert contagem.json() == {"total_nao_lidas": 0}

    def test_usuario_comum_nao_cria_notificacao_para_outra_pessoa(
        self, client, equipe, token_acesso
    ):
        resposta = client.post(
            "/notificacoes",
            json={
                "titulo": "Golpe",
                "mensagem": "texto",
                "funcionario_id": equipe.admin.funcionario_id,
            },
            headers=self._cabecalho(token_acesso, equipe.bruno),
        )

        assert resposta.status_code == 403
