from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.cargo import CargoCreate, CargoResponse
from app.services.cargo import CargoService

router = APIRouter(prefix="/cargos", tags=["Cargos"])


@router.get("", response_model=list[CargoResponse], status_code=status.HTTP_200_OK)
def buscar_todos_cargos(db: Session = Depends(get_db)):
    service = CargoService(db)
    return service.buscar_todos()


@router.post("", response_model=CargoResponse, status_code=status.HTTP_201_CREATED)
def criar_cargo(dados: CargoCreate, db: Session = Depends(get_db)):
    service = CargoService(db)
    try:
        return service.criar_cargo(dados)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
