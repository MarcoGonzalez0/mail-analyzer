import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers import scans, health
from app.database import engine, Base
from app.logging_config import setup_logging
from app.config import settings

logger = logging.getLogger(__name__)


# lifespan define el ciclo de vida completo de la app en una sola función.
# Todo lo que está antes del yield se ejecuta al arrancar (startup).
# Todo lo que está después del yield se ejecuta al apagarse (shutdown).
# Es el mismo patrón que get_db: abrís un recurso, hacés yield, cerrás el recurso.
#
# get_db    → ciclo de vida de un request HTTP  (abre sesión → yield → cierra sesión)
# lifespan  → ciclo de vida de la app completa  (startup     → yield → shutdown)
# engine    → solo para operaciones de estructura (CREATE TABLE), no de datos
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ───────────────────────────────────────────────────────────────
    setup_logging(environment=settings.environment)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # crea tablas si no existen

    yield  # la app vive aquí, atendiendo requests

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    # lugar natural para cerrar conexiones, liberar recursos, etc.
    await engine.dispose()  # cierra todas las conexiones del pool al apagarse


app = FastAPI(
    title="Mail Analyzer",
    version="1.0.0",
    lifespan=lifespan,  # le pasamos el ciclo de vida a FastAPI
)

# Registramos los routers bajo el prefijo /v1
app.include_router(scans.router, prefix="/v1")
app.include_router(health.router, prefix="/v1")


# ── GLOBAL EXCEPTION HANDLER (defensive programming / fail-safe defaults) ────
#
# Última línea de defensa: atrapa cualquier excepción que escape de un endpoint
# sin ser manejada (ej. DB muere a mitad de un query, bug inesperado).
#
# NO interviene cuando el error ya está controlado:
#   - Pydantic rechaza input inválido        → 422 (lo maneja FastAPI)
#   - raise HTTPException(404)               → 404 (lo maneja tu código)
#   - try/except en scan_service             → 200 con status="failed"
#
# Solo actúa cuando NADA más atrapó la excepción.
#
# @app.exception_handler(Exception) registra el handler en la app (no en un router)
# porque debe cubrir TODOS los endpoints. Exception es la clase base → atrapa todo.
# Se podría registrar handlers para tipos específicos (ValueError, SQLAlchemyError).
#
# Vive en main.py porque es donde se crea la instancia de FastAPI — el handler
# se registra directamente en `app`, la capa más externa antes del cliente.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # exc_info=exc incluye el stack trace completo en los logs (para el desarrollador)
    logger.error(f"Error no manejado en {request.url.path}", exc_info=exc)
    # Al cliente se le devuelve un JSON genérico sin detalles internos
    # (sin stack traces, rutas de archivos, ni nombres de librerías)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )