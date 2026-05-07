# Este archivo Schemas define los modelos de datos que se usarán para validar las solicitudes y respuestas de la API. Usamos Pydantic para esto, 
# lo que nos permite asegurarnos de que los datos sean correctos y tengan el formato esperado antes de procesarlos.

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

# Valida lo que llega desde el cliente en el POST /v1/scans
class ScanRequest(BaseModel):
    email: EmailStr
    headers: Optional[list[str]] = []

# Valida y define la estructura de la respuesta. 
# From_attributes=True le dice a Pydantic que puede construir este schema desde un objeto SQLAlchemy directamente
class ScanResponse(BaseModel):
    scan_id: uuid.UUID
    email: str
    domain: str
    status: str
    risk_score: Optional[int] = None
    results: Optional[dict] = None
    findings: Optional[list[str]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}



# Para la respuesta del GET /v1/scans, que devuelve una lista de escaneos, definimos otro schema que incluye el total y la lista de escaneos
class ScanListResponse(BaseModel):
    total: int
    scans: list[ScanResponse]