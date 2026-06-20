from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.schemas import HealthResponse

router = APIRouter()


# Este endpoint sirve a dos consumidores distintos con la misma llamada:
#
#   1. Docker healthcheck → solo le importa si recibe HTTP 200 (¿el proceso responde?).
#      No lee el JSON. Si no recibe respuesta, marca el contenedor como unhealthy.
#
#   2. Desarrollador / monitoreo → lee el JSON para saber el estado de las dependencias.
#      Si db="error", la API responde pero la DB está caída (status="degraded").
#
# Siempre devuelve 200 porque el contenedor ESTÁ vivo aunque la DB no — la distinción
# entre "ok" y "degraded" es información para quien lee el body, no para Docker.
@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "1.0.0",
        "db": db_status
    }