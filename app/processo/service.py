import logging
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.core.datajud_api import DatajudApiClient
from app.core.relatorio import (
    LIMITE_LINHAS,
    Arquivo,
    Coluna,
    FormatoRelatorio,
    Tabela,
    TipoColuna,
    gerar_arquivo,
)
from app.processo.model import Processo, StatusProcesso
from app.processo.repository import ProcessoRepository
from app.processo.schema import (
    ProcessoCreate,
    ProcessoFilter,
    ProcessoPaginadoResponse,
    ProcessoResponse,
    ProcessoUpdate,
)

logger = logging.getLogger(__name__)

STATUS_FINALIZADOS = [StatusProcesso.CONCLUIDO, StatusProcesso.ARQUIVADO]


class ProcessoService:
    def __init__(self, db_session: Session):
        self.repository = ProcessoRepository(db_session)

    def buscar_todos(self) -> list[Processo]:
        return self.repository.buscar_todos()

    def buscar_processos(self, filters: ProcessoFilter) -> ProcessoPaginadoResponse:
        itens, total = self.repository.buscar_paginado_por_filtros(
            page=filters.page,
            page_size=filters.page_size,
            processo_id=filters.processo_id,
            cnj=filters.cnj,
            titulo=filters.titulo,
            descricao=filters.descricao,
            status=filters.status,
            tribunal=filters.tribunal,
            area=filters.area,
            cliente_id=filters.cliente_id,
            funcionario_id=filters.funcionario_id,
            busca=filters.busca,
            prazo_inicio=filters.prazo_inicio,
            prazo_fim=filters.prazo_fim,
        )
        return ProcessoPaginadoResponse(
            itens=[ProcessoResponse.model_validate(processo) for processo in itens],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=max(1, ceil(total / filters.page_size)),
        )

    def exportar_processos(self, filters: ProcessoFilter, formato: FormatoRelatorio) -> Arquivo:
        processos = self.repository.buscar_para_exportacao(
            LIMITE_LINHAS + 1,
            processo_id=filters.processo_id,
            cnj=filters.cnj,
            titulo=filters.titulo,
            descricao=filters.descricao,
            status=filters.status,
            tribunal=filters.tribunal,
            area=filters.area,
            cliente_id=filters.cliente_id,
            funcionario_id=filters.funcionario_id,
            busca=filters.busca,
            prazo_inicio=filters.prazo_inicio,
            prazo_fim=filters.prazo_fim,
        )
        if len(processos) > LIMITE_LINHAS:
            raise ValueError(
                f"A exportação excede {LIMITE_LINHAS} processos; refine os filtros e tente novamente"
            )
        clientes = self.repository.buscar_nomes_clientes({p.cliente_id for p in processos})
        tabela = Tabela(
            titulo="Relatório de Processos",
            colunas=[
                Coluna("CNJ"),
                Coluna("Título"),
                Coluna("Descrição"),
                Coluna("Status"),
                Coluna("Tribunal"),
                Coluna("Área"),
                Coluna("Cliente"),
                Coluna("Data de início", TipoColuna.DATA),
                Coluna("Prazo", TipoColuna.DATA),
                Coluna("Data realizado", TipoColuna.DATA),
            ],
            linhas=[
                [
                    p.cnj,
                    p.titulo,
                    p.descricao,
                    p.status.value,
                    p.tribunal,
                    p.area,
                    clientes.get(p.cliente_id),
                    p.data_inicio,
                    p.data_prazo,
                    p.data_realizado,
                ]
                for p in processos
            ],
        )
        return gerar_arquivo(tabela, formato)

    def criar_processo(self, dados: ProcessoCreate) -> Processo:
        processo_existente = self.repository.buscar_por_cnj(dados.cnj)

        if processo_existente:
            raise ValueError("Processo já cadastrado")
        processo_model = Processo(**dados.model_dump())
        return self.repository.criar(processo_model)

    def atualizar_processo(self, processo_id: int, dados: ProcessoUpdate) -> Processo:
        processo = self.repository.buscar_por_id(processo_id)

        if processo is None:
            raise ValueError("Processo não encontrado")
        dados_atualizacao = dados.model_dump(exclude_unset=True)

        if "cnj" in dados_atualizacao:
            processo_existente = self.repository.buscar_por_cnj(dados_atualizacao["cnj"])

            if processo_existente is not None and processo_existente.processo_id != processo_id:
                raise ValueError("CNJ já cadastrado")

        for key, value in dados_atualizacao.items():
            setattr(processo, key, value)
        return self.repository.atualizar(processo)

    def deletar_processo(self, processo_id: int) -> None:
        processo = self.repository.buscar_por_id(processo_id)

        if processo is None:
            raise ValueError("Processo não encontrado")
        self.repository.deletar(processo)

    def buscar_processos_criticos(
        self,
        dias_sem_movimentacao: int = 30,
        funcionario_id: int | None = None,
    ) -> list[ProcessoResponse]:
        data_limite = datetime.now(UTC) - timedelta(days=dias_sem_movimentacao)
        processos = self.repository.buscar_por_filtros(
            status_excluidos=STATUS_FINALIZADOS,
            ultima_atividade_ate=data_limite,
            funcionario_id=funcionario_id,
        )
        return [ProcessoResponse.model_validate(p) for p in processos]

    @classmethod
    async def sincronizar_processos_com_api(cls) -> int:
        db = SessionLocal()
        try:
            api_client = DatajudApiClient()

            processos = db.query(Processo).filter(Processo.cnj.is_not(None)).all()

            updates_count = 0
            for processo in processos:
                if not processo.cnj:
                    continue

                data = await api_client.fetch_processo(processo.cnj)
                if data:
                    if "status" in data and data["status"]:
                        raw_status = data["status"]
                        status_map = {
                            "Em Andamento": StatusProcesso.ATIVO,
                            "Ativo": StatusProcesso.ATIVO,
                            "Em Recurso": StatusProcesso.ATIVO,
                            "Concluso para Decisão": StatusProcesso.EM_ANALISE,
                            "Em Análise": StatusProcesso.EM_ANALISE,
                            "Concluído": StatusProcesso.CONCLUIDO,
                            "Julgado": StatusProcesso.CONCLUIDO,
                            "Arquivado": StatusProcesso.ARQUIVADO,
                        }
                        processo.status = status_map.get(raw_status, StatusProcesso.ATIVO)
                    if "data_realizado" in data and data["data_realizado"]:
                        processo.data_realizado = data["data_realizado"]
                    if "tribunal" in data and data["tribunal"]:
                        processo.tribunal = data["tribunal"]

                    updates_count += 1

            if updates_count > 0:
                db.commit()
                logger.info(
                    f"[JOB SYNC] {updates_count} processos atualizados com sucesso via Datajud API."
                )
            return updates_count
        except Exception as e:
            db.rollback()
            logger.error(f"[JOB SYNC] Falha ao sincronizar processos: {e}")
            raise
        finally:
            db.close()
