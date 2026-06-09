from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.routers import scans, health
from app.database import engine, Base
from app.logging_config import setup_logging
from app.config import settings


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