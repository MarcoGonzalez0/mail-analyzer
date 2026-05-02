from fastapi import APIRouter

router = APIRouter()

@router.post("/scans")
async def create_scan():
    return {"message": "not implemented yet"}

@router.get("/scans")
async def list_scans():
    return {"message": "not implemented yet"}

@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str):
    return {"message": "not implemented yet"}