from fastapi import APIRouter # Importamos APIRouter para crear un router específico para las rutas de salud

router = APIRouter()

@router.get("/health") # evita usar verbos en la ruta, el verbo ya está dado por el método HTTP (GET)
async def health_check():
    return {"status": "ok",
            "db": "connected",
            "version": "1.0.0"}