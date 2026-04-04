# app/api/v1/endpoints/analysis/chart.py
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/chart/{filename}")
async def get_chart(filename: str, key: int = 0):
    """Serve chart images with cache busting."""
    charts_dir = os.path.join(os.getcwd(), "agents", "charts")
    file_path = os.path.join(charts_dir, filename)

    # Security: Prevent directory traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chart not found")

    return FileResponse(file_path, media_type="image/png", filename=filename)


__all__ = ['router']