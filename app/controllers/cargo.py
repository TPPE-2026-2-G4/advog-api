from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.cargo import CargoCreate, CargoResponse, CargoUpdate
from app.services.cargo import CargoService

router = APIRouter(prefix="/cargos", tags=["Cargos"])


@router.get("", response_model=list[CargoResponse], status_code=status.HTTP_200_OK)
def buscar_todos_cargos(db: Session = Depends(get_db)):
    service = CargoService(db)
    return service.buscar_todos()


@router.get("/{cargo_id}", response_model=CargoResponse, status_code=status.HTTP_200_OK)
def buscar_cargo_por_id(cargo_id: int, db: Session = Depends(get_db)):
    service = CargoService(db)
    try:
        return service.buscar_por_id(cargo_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("", response_model=CargoResponse, status_code=status.HTTP_201_CREATED)
def criar_cargo(dados: CargoCreate, db: Session = Depends(get_db)):
    service = CargoService(db)
    try:
        return service.criar_cargo(dados)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/{cargo_id}", response_model=CargoResponse, status_code=status.HTTP_200_OK)
def atualizar_cargo(cargo_id: int, dados: CargoUpdate, db: Session = Depends(get_db)):
    service = CargoService(db)
    try:
        return service.atualizar_cargo(cargo_id, dados)
    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(e) == "Cargo não encontrado"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e)) from e
