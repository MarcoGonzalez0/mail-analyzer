from fastapi import FastAPI
from app.routers import scans, health
from app.database import engine, Base

app = FastAPI(
    title="Mail Analyzer",
    version="1.0.0",
)

# Evento de inicio para crear las tablas en la base de datos si no existen
# Esto asegura que la tabla "scans" se cree automáticamente al iniciar la aplicación, evitando errores relacionados con tablas faltantes.
# No usa get_db porque get_db está diseñado para el ciclo de vida de un request HTTP
# get_db    → para operaciones de datos (INSERT, SELECT)
# engine    → para operaciones de estructura (CREATE TABLE)
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(scans.router, prefix="/v1")
app.include_router(health.router, prefix="/v1")