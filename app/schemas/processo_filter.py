from fastapi import Query


class ProcessoFilter:
    def __init__(
        self,
        processo_id: int | None = Query(None, description="Filtrar por ID do processo"),
        cnj: str | None = Query(None, description="Filtrar por CNJ"),
        titulo: str | None = Query(None, description="Filtrar por título"),
        descricao: str | None = Query(None, description="Filtrar por descrição"),
        status: str | None = Query(None, description="Filtrar por status"),
        tribunal: str | None = Query(None, description="Filtrar por tribunal"),
        area: str | None = Query(None, description="Filtrar por área"),
        cliente_id: int | None = Query(None, description="Filtrar por ID do cliente"),
    ):
        self.processo_id = processo_id
        self.cnj = cnj
        self.titulo = titulo
        self.descricao = descricao
        self.status = status
        self.tribunal = tribunal
        self.area = area
        self.cliente_id = cliente_id
