# El archivo scan_service.py contiene la lógica de negocio para manejar los escaneos. 
# Aquí es donde se implementan las funciones para crear un nuevo escaneo, obtener un 
# escaneo por ID y listar todos los escaneos. Estas funciones interactúan con la base 
# de datos utilizando SQLAlchemy y aplican las reglas de evaluación para calcular el 
# riesgo del correo electrónico analizado.

from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings

from app.services.spf import analyze_spf
from app.services.dmarc import analyze_dmarc
from app.services.whois import analyze_whois

from app.models.scan import Scan
from app.schemas import ScanRequest
from datetime import datetime, timezone
import httpx

from app.logging_config import get_logger # Importamos el logger para usarlo en esta capa de servicios

logger = get_logger()

# Contrato de retorno de _run_analysis: define exactamente qué llaves y tipos devuelve.
# Usar TypedDict en lugar de dict genérico permite autocompletado y detección de errores en el editor.
class AnalysisResult(TypedDict):
    results:    dict        # datos crudos del scanner Go + análisis Python ensamblados
    findings:   list[str]  # lista de IDs de reglas violadas (ej: "no_spf", "dmarc_none")
    risk_score: int         # puntuación final 0–100

# Cada regla tiene un ID que identifica el problema, una penalización al score y una descripción legible.
# Tipar la lista como list[Rule] permite que el editor detecte typos en las claves ("penality" vs "penalty").
class Rule(TypedDict):
    id:          str  # identificador único de la regla, coincide con los findings
    penalty:     int  # puntos que se restan del score (0–100) cuando la regla se viola
    description: str  # descripción legible del problema para logs y respuestas

RULES: list[Rule] = [
    {"id": "no_spf",              "penalty": 20, "description": "No SPF record found"},
    {"id": "weak_spf",            "penalty": 25, "description": "SPF uses +all, anyone can send"},
    {"id": "soft_spf",            "penalty": 10, "description": "SPF uses ~all, weak policy"},
    {"id": "neutral_spf",         "penalty": 15, "description": "SPF uses ?all, no policy"},
    {"id": "no_dmarc",            "penalty": 20, "description": "No DMARC record found"},
    {"id": "dmarc_none",          "penalty": 15, "description": "DMARC policy is none, no action taken"},
    {"id": "dmarc_quarantine",    "penalty": 5,  "description": "DMARC policy is quarantine, not fully strict"},
    {"id": "dmarc_partial",       "penalty": 5,  "description": "DMARC not applied to all emails"},
    {"id": "no_mx",               "penalty": 15, "description": "No MX records found"},
    {"id": "domain_expiring_soon","penalty": 10, "description": "Domain expires in less than 30 days"},
]

def calculate_risk_score(findings: list[str]) -> int:
    penalty = sum(r["penalty"] for r in RULES if r["id"] in findings)
    return max(0, 100 - penalty)

def extract_domain(email: str) -> str:
    return email.split("@")[1]

async def _run_analysis(domain: str) -> AnalysisResult:
    """
    Orquesta el análisis completo de un dominio:
    llama al scanner Go (DNS), corre los analizadores Python (SPF, DMARC, MX, WHOIS)
    y ensambla el resultado listo para guardar en DB.
    """
    scanner_result = await call_scanner(domain)
    dns_result = scanner_result.get("dns", {})

    findings: list[str] = []
    analysis: dict = {}

    # SPF — ¿puede cualquiera enviar email fingiendo ser este dominio?
    spf_analysis = analyze_spf(dns_result.get("txt_records") or [])
    analysis["spf"] = spf_analysis
    findings.extend(spf_analysis["findings"])

    # DMARC — ¿qué hace el servidor receptor con emails que fallan SPF/DKIM?
    dmarc_analysis = analyze_dmarc(domain, dns_result.get("dmarc_records") or [])
    analysis["dmarc"] = dmarc_analysis
    findings.extend(dmarc_analysis["findings"])

    # MX — sin registros MX el dominio no está configurado para recibir correo
    if not dns_result.get("has_mx"):
        findings.append("no_mx")

    # WHOIS — información de registro: quién es el dueño y cuándo expira
    whois_analysis = analyze_whois(domain)
    analysis["whois"] = whois_analysis
    findings.extend(whois_analysis["findings"])

    return AnalysisResult(
        results={**scanner_result, "analysis": analysis},  # datos crudos Go + análisis Python
        findings=findings,
        risk_score=calculate_risk_score(findings),
    )

# Esta función se encarga de llamar al escaner de GO, enviándole el dominio a analizar.
async def call_scanner(domain: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(settings.scanner_url, json={"domain": domain})
        response.raise_for_status()
        return response.json()

# La función create_scan es la función principal que se llama para crear un nuevo escaneo.
async def create_scan(db: AsyncSession, payload: ScanRequest) -> Scan:
    domain = extract_domain(payload.email)
    logger.info("=============================================================")
    logger.info(f"Creando nuevo escaneo para {payload.email} (dominio: {domain})") # Logueamos la creación del escaneo con el email y dominio

    scan = Scan(
        email=payload.email,
        domain=domain,
        status="pending",
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    try:
        outcome = await _run_analysis(domain)

        # Actualizo el escaneo con los resultados y análisis obtenidos
        scan.status      = "completed"
        scan.results     = outcome["results"]
        scan.findings    = outcome["findings"]
        scan.risk_score  = outcome["risk_score"]
        scan.completed_at = datetime.now(timezone.utc)

    except Exception as e:
        scan.status = "failed"
        logger.error(f"Error al analizar {payload.email}: {str(e)}") # Logueamos el error con el email que causó el problema

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