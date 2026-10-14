from pydantic import BaseModel


class ProdutividadeResponse(BaseModel):
    funcionario_id: int
    nome: str
    finalizadas: int
    em_andamento: int
    a_fazer: int
    atrasadas: int
    progresso: float
