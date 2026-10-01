import logging

from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.processo.model import Processo
from app.processo.repository import ProcessoRepository
from app.processo.schema import ProcessoCreate, ProcessoFilter
from app.utils.jusbrasil_api import JusbrasilApiClient

logger = logging.getLogger(__name__)


class ProcessoService:
    def __init__(self, db_session: Session):
        self.repository = ProcessoRepository(db_session)

    def create_processo(self, processo_data: ProcessoCreate) -> Processo:
        processo_model = Processo(**processo_data.model_dump())
        return self.repository.save(processo_model)

    def search_processos(self, filters: ProcessoFilter) -> list[Processo]:
        return self.repository.find_all_by_filters(
            processo_id=filters.processo_id,
            cnj=filters.cnj,
            titulo_proc=filters.titulo_proc,
            descricao_proc=filters.descricao_proc,
            status=filters.status,
            tribunal=filters.tribunal,
            area=filters.area,
            cliente_id=filters.cliente_id,
            responsavel_id=filters.responsavel_id,
        )

    @classmethod
    async def sincronizar_processos_com_api(cls):

        db = SessionLocal()
        try:
            api_client = JusbrasilApiClient()

            processos = db.query(Processo).filter(Processo.cnj != None).all()  # noqa: E711

            updates_count = 0
            for processo in processos:
                if not processo.cnj:
                    continue

                data = await api_client.fetch_processo(processo.cnj)
                if data:
                    if "status" in data and data["status"]:
                        processo.status = data["status"]
                    if "data_realizado" in data and data["data_realizado"]:
                        processo.data_realizado = data["data_realizado"]
                    if "tribunal" in data and data["tribunal"]:
                        processo.tribunal = data["tribunal"]

                    updates_count += 1

            if updates_count > 0:
                db.commit()
                logger.info(
                    f"[JOB SYNC] {updates_count} processos atualizados com sucesso via Jusbrasil API."
                )
        except Exception as e:
            db.rollback()
            logger.error(f"[JOB SYNC] Falha ao sincronizar processos: {e}")
        finally:
            db.close()
