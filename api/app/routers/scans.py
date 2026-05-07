from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db # Importo dependency para obtener la sesión de base de datos
from app.schemas import ScanRequest, ScanResponse, ScanListResponse # Importo los schemas que definen la estructura de las solicitudes y respuestas
from app.services import scan_service # Importo el servicio que contiene la lógica de negocio para manejar los escaneos

router = APIRouter()

# /v1/scans - POST: Crea un nuevo escaneo
@router.post("/scans", response_model=ScanResponse)
async def create_scan(payload: ScanRequest, db: AsyncSession = Depends(get_db)):
    scan = await scan_service.create_scan(db, payload)
    return scan

# /v1/scans - GET: Lista todos los escaneos realizados
@router.get("/scans", response_model=ScanListResponse)
async def list_scans(db: AsyncSession = Depends(get_db)):
    scans = await scan_service.list_scans(db)
    return {"total": len(scans), 
            "scans": scans}

# /v1/scans/{scan_id} - GET: Obtiene los detalles de un escaneo específico por su ID
@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan = await scan_service.get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan