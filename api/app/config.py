from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    database_url: str # espera encontrar DATABASE_URL en el entorno

    class Config: # Clase de configuración para pydantic, que especifica que las variables de entorno se cargarán desde un archivo .env
        env_file = ".env" # busca las variables en este archivo

settings = Settings() # al instanciarse, lee el .env automáticamente

# Lo que hace Pydantic aquí es leer las variables de entorno y validar que existan antes de que la app arranque. Si DATABASE_URL no está definida, la app falla inmediatamente con un error claro en vez de fallar misteriosamente después.
# La clase Config le dice dónde buscar las variables. Sin ella, solo buscaría en las variables de entorno del sistema, no en el .env.