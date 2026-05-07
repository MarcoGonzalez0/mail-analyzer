from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession # para crear una conexión asíncrona a la base de datos y manejar sesiones asíncronas
from sqlalchemy.orm import DeclarativeBase, sessionmaker # para crear sesiones y definir modelos de base de datos
from app.config import settings # buscar URL de la database

# Crear el motor de la base de datos asíncrona utilizando la URL proporcionada en la configuración
engine = create_async_engine(settings.database_url, echo=True)

# Crear una clase de sesión asíncrona utilizando sessionmaker, que se utilizará para interactuar con la base de datos
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False # evitar que objetos se vuelvan obsoletos después de una confirmación de transacción
)

class Base(DeclarativeBase): # clase base para definir modelos de la base de datos utilizando SQLAlchemy ORM
    pass

# Dependencia para obtener una sesión de base de datos asíncrona, que se puede usar en rutas de FastAPI para interactuar con la base de datos
# De esta manera, cada vez que se necesite una sesión de base de datos, se creará una nueva sesión asíncrona y se cerrará automáticamente después de su uso
# Esto evita escribir codigo repetitivo
async def get_db():
    async with AsyncSessionLocal() as session:
        # esto significa que existe una sesion nueva cada vez que se llama a esta dependencia
        yield session # Generar sesión


