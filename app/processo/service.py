import logging
from datetime import UTC, datetime, timedelta
from math import ceil

import filetype
from fastapi import UploadFile
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
from app.core.storage import obter_url_publica, remover_arquivo, salvar_arquivo
from app.funcionario.model import Funcionario
from app.processo.model import DocumentoProcesso, Processo, StatusProcesso
from app.processo.repository import ProcessoRepository
from app.processo.schema import (
    DocumentoProcessoResponse,
    ProcessoCreate,
    ProcessoFilter,
    ProcessoPaginadoResponse,
    ProcessoResponse,
    ProcessoResumoResponse,
    ProcessoUpdate,
)

logger = logging.getLogger(__name__)

STATUS_FINALIZADOS = [StatusProcesso.CONCLUIDO, StatusProcesso.ARQUIVADO]
TAMANHO_MAXIMO_DOCUMENTO = 25 * 1024 * 1024  # 25MB
EXTENSOES_PERMITIDAS = {"pdf", "docx", "doc", "png", "jpg", "jpeg"}
CARGOS_ADMINISTRADOR = ("administrador", "admin")


class ProcessoService:
    def __init__(self, db_session: Session):
        self.repository = ProcessoRepository(db_session)

    @staticmethod
    def _eh_administrador(usuario: Funcionario | None) -> bool:
        if usuario is None:
            return True
        cargo = getattr(usuario, "cargo", None)
        if cargo is None:
            return False
        nome_cargo = (cargo.nome_cargo or "").strip().lower()
        permissoes = cargo.permissao or {}
        return nome_cargo in CARGOS_ADMINISTRADOR or bool(
            permissoes.get("configuracoes_sistema", False)
        )

    def obter_resumo_processos(
        self,
        usuario: Funcionario | None = None,
        funcionario_id: int | None = None,
        dias_proximo_prazo: int = 7,
    ) -> ProcessoResumoResponse:
        filtro_funcionario_id = (
            funcionario_id
            if self._eh_administrador(usuario)
            else getattr(usuario, "funcionario_id", None)
        )

        contagens = self.repository.contar_por_status(funcionario_id=filtro_funcionario_id)
        em_andamento = contagens.get(StatusProcesso.ATIVO, 0)
        em_analise = contagens.get(StatusProcesso.EM_ANALISE, 0)
        finalizados = contagens.get(StatusProcesso.CONCLUIDO, 0)
        total = em_andamento + em_analise + finalizados

        hoje = datetime.now(UTC).date()
        atrasados = self.repository.contar_por_filtros(
            status_excluidos=STATUS_FINALIZADOS,
            funcionario_id=filtro_funcionario_id,
            prazo_fim=hoje - timedelta(days=1),
        )
        proximos_do_prazo = self.repository.contar_por_filtros(
            status_excluidos=STATUS_FINALIZADOS,
            funcionario_id=filtro_funcionario_id,
            prazo_inicio=hoje,
            prazo_fim=hoje + timedelta(days=dias_proximo_prazo),
        )

        return ProcessoResumoResponse(
            total=total,
            em_andamento=em_andamento,
            em_analise=em_analise,
            finalizados=finalizados,
            proximos_do_prazo=proximos_do_prazo,
            atrasados=atrasados,
        )

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

        documentos = self.repository.listar_documentos(processo_id)
        for doc in documentos:
            remover_arquivo(doc.chave_minio)

        self.repository.deletar(processo)

    def adicionar_documento(
        self,
        processo_id: int,
        file: UploadFile,
        funcionario_id: int | None = None,
        origem: str = "manual",
    ) -> DocumentoProcessoResponse:
        processo = self.repository.buscar_por_id(processo_id)
        if processo is None:
            raise ValueError("Processo não encontrado")

        conteudo = file.file.read()
        file.file.seek(0)
        tamanho_bytes = len(conteudo)

        if tamanho_bytes == 0:
            raise ValueError("O arquivo enviado está vazio.")

        if tamanho_bytes > TAMANHO_MAXIMO_DOCUMENTO:
            raise ValueError("O arquivo excede o limite máximo permitido de 25MB.")

        nome_original = file.filename or "documento"
        extensao = nome_original.rsplit(".", 1)[-1].lower() if "." in nome_original else ""

        if extensao not in EXTENSOES_PERMITIDAS:
            raise ValueError(
                f"Extensão de arquivo não permitida. Extensões aceitas: {', '.join(sorted(EXTENSOES_PERMITIDAS))}"
            )

        tipo_detectado = filetype.guess(conteudo)
        if extensao in {"pdf", "png", "jpg", "jpeg"} and (
            not tipo_detectado or tipo_detectado.extension not in {"pdf", "png", "jpg", "jpeg"}
        ):
            raise ValueError("O conteúdo do arquivo não corresponde a um formato válido.")

        content_type = file.content_type or (
            tipo_detectado.mime if tipo_detectado else "application/octet-stream"
        )

        chave_minio = salvar_arquivo(
            conteudo=file.file,
            extensao=extensao,
            content_type=content_type,
            pasta=f"processos/{processo_id}",
        )

        try:
            documento = DocumentoProcesso(
                processo_id=processo_id,
                nome_original=nome_original,
                chave_minio=chave_minio,
                origem=origem,
                tamanho_bytes=tamanho_bytes,
                entrada_tipo=content_type,
                funcionario_id=funcionario_id,
                data_upload=datetime.utcnow(),
            )
            documento_salvo = self.repository.adicionar_documento(documento)
            resposta = DocumentoProcessoResponse.model_validate(documento_salvo)
            resposta.url = obter_url_publica(documento_salvo.chave_minio)
            return resposta
        except Exception:
            remover_arquivo(chave_minio)
            raise

    def listar_documentos(self, processo_id: int) -> list[DocumentoProcessoResponse]:
        processo = self.repository.buscar_por_id(processo_id)
        if processo is None:
            raise ValueError("Processo não encontrado")

        documentos = self.repository.listar_documentos(processo_id)
        respostas = []
        for doc in documentos:
            item = DocumentoProcessoResponse.model_validate(doc)
            item.url = obter_url_publica(doc.chave_minio)
            respostas.append(item)
        return respostas

    def obter_url_documento(
        self, processo_id: int, documento_id: int, expiracao_segundos: int = 1800
    ) -> str:
        documento = self.repository.buscar_documento_por_id(documento_id)
        if documento is None or documento.processo_id != processo_id:
            raise ValueError("Documento não encontrado")

        url = obter_url_publica(documento.chave_minio, expiracao_segundos=expiracao_segundos)
        if not url:
            raise ValueError("Falha ao gerar URL de acesso ao documento")
        return url

    def remover_documento(self, processo_id: int, documento_id: int) -> None:
        documento = self.repository.buscar_documento_por_id(documento_id)
        if documento is None or documento.processo_id != processo_id:
            raise ValueError("Documento não encontrado")

        self.repository.deletar_documento(documento)
        remover_arquivo(documento.chave_minio)

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
