from fastapi import FastAPI
from app.routers import scans, health 

app = FastAPI(
    title="Mail Analyzer",
    version="1.0.0",
)

app.include_router(scans.router, prefix="/v1")
app.include_router(health.router, prefix="/v1")