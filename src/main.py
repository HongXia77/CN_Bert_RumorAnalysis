from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.user_related_logic import router as user_router
from src.service import quick_source_service
from src.utils.db import SessionLocal, initialize_database


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MAPS_DIR = BASE_DIR.parent / "frontend" / "public" / "maps"


app = FastAPI(title="CN Bert Rumor Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/api/user", tags=["用户模块"])
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup_event():
    initialize_database()
    db = SessionLocal()
    try:
        quick_source_service.ensure_default_quick_sources(db)
    finally:
        db.close()


@app.get("/api/maps/{map_name}")
async def get_map_geojson(map_name: str):
    safe_name = Path(map_name).stem
    file_candidates = [
        MAPS_DIR / f"{safe_name}.json",
        MAPS_DIR / f"{safe_name}.geojson",
    ]

    for file_path in file_candidates:
        if file_path.exists():
            return FileResponse(file_path, media_type="application/json")

    raise HTTPException(status_code=404, detail=f"Map data for '{safe_name}' not found.")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
