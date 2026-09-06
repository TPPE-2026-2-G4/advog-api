import enum

from sqlalchemy import Boolean, CheckConstraint, Column, Enum, Integer, String

from app.config.database import Base


class StatusFuncionario(enum.StrEnum):
    PENDENTE = "Pendente"
    ATIVO = "Ativo"
    INATIVO = "Inativo"


class Funcionario(Base):
    __tablename__ = "funcionarios"

    funcionario_id = Column(Integer, primary_key=True, index=True)
    uf_oab = Column(String(2), nullable=True)
    numero_oab = Column(String(5), nullable=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=True)
    status = Column(Enum(StatusFuncionario), nullable=False, default=StatusFuncionario.PENDENTE)
    exibicaoInstitucional = Column(Boolean, nullable=False, default=False)

    # TODO: APAGAR LINHAS ABAIXO QUANDO TABELA CARGOS FOR IMPLEMENTADA
    # cargo_id = Column(Long, ForeignKey("cargos.cargo_id"), nullable=False)

    # cargos = relationship("Cargo", back_populates="funcionarios")

    __table_args__ = (
        CheckConstraint("uf_oab IS NULL OR length(uf_oab) = 2", name="ck_uf_oab_tamanho"),
        CheckConstraint(
            "numero_oab IS NULL OR length(numero_oab) = 5", name="ck_numero_oab_tamanho"
        ),
    )
