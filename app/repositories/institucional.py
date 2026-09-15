from sqlalchemy.orm import Session

from app.models.institucional import Institucional


class InstitucionalNaoEncontradoError(Exception):
    pass


class InstitucionalRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_configuracoes(self) -> Institucional:
        institucional = self.db.get(Institucional, 1)
        if institucional is None:
            raise InstitucionalNaoEncontradoError(
                "Configuração do site institucional não encontrada."
            )
        return institucional

    def atualizar_configuracoes(self, dados: dict) -> Institucional:
        config = self.buscar_configuracoes()
        for campo, valor in dados.items():
            if hasattr(config, campo):
                setattr(config, campo, valor)
        self.db.commit()
        self.db.refresh(config)
        return config
