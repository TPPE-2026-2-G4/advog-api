from sqlalchemy.orm import Session

from app.atuacao.model import Atuacao
from app.funcionario.model import Funcionario


class AtuacaoRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def buscar_todas(self) -> list[Atuacao]:
        return self.db.query(Atuacao).order_by(Atuacao.atuacao_id).all()

    def buscar_visiveis_institucional(self) -> list[Atuacao]:
        return (
            self.db.query(Atuacao)
            .filter(Atuacao.exibicao_institucional.is_(True))
            .order_by(Atuacao.atuacao_id)
            .all()
        )

    def buscar_por_id(self, atuacao_id: int) -> Atuacao | None:
        return self.db.get(Atuacao, atuacao_id)

    def buscar_por_nome(self, nome: str) -> Atuacao | None:
        return self.db.query(Atuacao).filter_by(nome=nome).first()

    def possui_funcionarios(self, atuacao_id: int) -> bool:
        return self.db.query(Funcionario).filter_by(atuacao_id=atuacao_id).first() is not None

    def criar(self, atuacao: Atuacao) -> Atuacao:
        self.db.add(atuacao)
        self.db.commit()
        self.db.refresh(atuacao)
        return atuacao

    def atualizar(self, atuacao: Atuacao) -> Atuacao:
        self.db.commit()
        self.db.refresh(atuacao)
        return atuacao

    def deletar(self, atuacao: Atuacao) -> Atuacao:
        self.db.delete(atuacao)
        self.db.commit()
        return atuacao
