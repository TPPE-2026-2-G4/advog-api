from fastapi import Query
from typing import Optional

class ProcessoFilter:
    def __init__(
        self,
        id: Optional[str] = Query(None, description="Filtrar por número do processo (id)"),
        tribunal: Optional[str] = Query(None, description="Filtrar por tribunal"),
        titulo: Optional[str] = Query(None, description="Filtrar por título"),
        cliente: Optional[str] = Query(None, description="Filtrar por cliente"),
        area: Optional[str] = Query(None, description="Filtrar por área"),
        responsavel: Optional[str] = Query(None, description="Filtrar por responsável"),
        status: Optional[str] = Query(None, description="Filtrar por status"),
        prazo: Optional[str] = Query(None, description="Filtrar por prazo")
    ):
        self.id = id
        self.tribunal = tribunal
        self.titulo = titulo
        self.cliente = cliente
        self.area = area
        self.responsavel = responsavel
        self.status = status
        self.prazo = prazo
