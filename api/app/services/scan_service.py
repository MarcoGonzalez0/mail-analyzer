# El archivo scan_service.py contiene la lógica de negocio para manejar los escaneos. 
# Aquí es donde se implementan las funciones para crear un nuevo escaneo, obtener un 
# escaneo por ID y listar todos los escaneos. Estas funciones interactúan con la base 
# de datos utilizando SQLAlchemy y aplican las reglas de evaluación para calcular el 
# riesgo del correo electrónico analizado.

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.scan import Scan
from app.schemas import ScanRequest
from datetime import datetime, timezone

RULES = [
    {"id": "no_spf",     "penalty": 20, "description": "No SPF record found"},
    {"id": "weak_spf",   "penalty": 10, "description": "SPF uses +all"},
    {"id": "no_dmarc",   "penalty": 20, "description": "No DMARC record found"},
    {"id": "dmarc_none", "penalty": 10, "description": "DMARC policy is none"},
    {"id": "no_mx",      "penalty": 15, "description": "No MX records found"},
]

def calculate_risk_score(findings: list[str]) -> int:
    penalty = sum(r["penalty"] for r in RULES if r["id"] in findings)
    return max(0, 100 - penalty)

def extract_domain(email: str) -> str:
    return email.split("@")[1]

async def create_scan(db: AsyncSession, payload: ScanRequest) -> Scan:
    domain = extract_domain(payload.email)

    scan = Scan(
        email=payload.email,
        domain=domain,
        status="pending",
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan

async def get_scan(db: AsyncSession, scan_id: str) -> Scan | None:
    result = await db.execute(select(Scan).where(Scan.scan_id == scan_id))
    return result.scalar_one_or_none()

async def list_scans(db: AsyncSession) -> list[Scan]:
    result = await db.execute(select(Scan).order_by(Scan.created_at.desc()))
    return result.scalars().all()


# Sí, services/ es donde va el grueso del programa. Es el corazón de la aplicación. 
# Los routers son solo la puerta de entrada HTTP, los models son solo la representación de la DB. 
# Todo lo interesante vive en los services.