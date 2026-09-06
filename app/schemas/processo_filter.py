from fastapi import Query


class ProcessoFilter:
    def __init__(
        self,
        id: str | None = Query(None, description="Filtrar por número do processo (id)"),
        tribunal: str | None = Query(None, description="Filtrar por tribunal"),
        titulo: str | None = Query(None, description="Filtrar por título"),
        cliente: str | None = Query(None, description="Filtrar por cliente"),
        area: str | None = Query(None, description="Filtrar por área"),
        responsavel: str | None = Query(None, description="Filtrar por responsável"),
        status: str | None = Query(None, description="Filtrar por status"),
        prazo: str | None = Query(None, description="Filtrar por prazo"),
    ):
        self.id = id
        self.tribunal = tribunal
        self.titulo = titulo
        self.cliente = cliente
        self.area = area
        self.responsavel = responsavel
        self.status = status
        self.prazo = prazo
