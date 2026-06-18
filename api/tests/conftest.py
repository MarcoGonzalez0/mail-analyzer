"""
conftest.py es el archivo de fixtures compartidas de pytest.
pytest lo carga automáticamente antes de correr los tests — no hay que importarlo.

Fixtures definidas aquí:
  db_session → sesión de PostgreSQL limpia por cada test
  client     → cliente HTTP que habla con FastAPI en memoria (sin servidor real)

Esto es para que los test usan sesiones de DB y clientes HTTP que controlamos, en lugar de los reales que usa la app en producción.
Cada vez que se inician los test de integracion, se leerá este archivo y se crearán estas fixtures. 
Luego, los test pueden pedir estas fixtures como argumentos de sus funciones, y pytest se encargará de inyectarlas automáticamente.
"""

import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base

# URL de la base de datos de TEST — separada de la de desarrollo.
# Si existe TEST_DATABASE_URL la usamos (CI la define). Si no, apuntamos
# al servicio db-test del docker-compose (puerto 5433, base mailanalyzer_test).
# Esto protege tus datos de desarrollo: los tests NUNCA tocan la DB principal.
_test_db_url = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@db-test:5432/mailanalyzer_test",
)


@pytest_asyncio.fixture
async def db_session():
    """
    Sesión de base de datos para tests de integración.

    El engine se crea DENTRO del fixture (no a nivel de módulo) porque
    pytest-asyncio crea un event loop nuevo por cada test. Si el engine
    fuera global, el segundo test intentaría usar conexiones vinculadas
    al loop del test anterior → RuntimeError.
    """
    engine = create_async_engine(_test_db_url)
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSession() as session:
        yield session

        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()

    # Cerrar el pool de conexiones para no dejar conexiones huérfanas
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """
    Cliente HTTP que habla con FastAPI directamente en memoria.

    ASGITransport(app=app) → convierte el app ASGI en una función llamable.
    No levanta un servidor real en ningún puerto. La llamada HTTP nunca sale a la red.

    dependency_overrides → le dice a FastAPI "cuando alguien pida get_db,
    dame esta sesión de test en lugar de abrir una sesión real".
    Así los datos que escribe el endpoint van a la DB que controla el test.
    """
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db # sobreescribe get_db para que use la sesión de test

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    # Limpiar el override al terminar para no contaminar otros tests
    app.dependency_overrides.clear()
