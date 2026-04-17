# src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# ---> 1. 导入你刚刚写的路由
from src.api.user_related_logic import router as user_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---> 2. 注册路由，加上 /api/user 前缀
app.include_router(user_router, prefix="/api/user", tags=["用户模块"])

app.mount("/static", StaticFiles(directory="static"), name="static")

MAPS_DIR = os.path.join(os.path.dirname(__file__), "data", "maps")

@app.get("../frontend/public/maps/{map_name}")
async def get_map_geojson(map_name: str):
    safe_file_name = os.path.basename(map_name)
    file_path = os.path.join(MAPS_DIR, f"{safe_file_name}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Map data for '{safe_file_name}' not found.")
    return FileResponse(file_path, media_type="application/json")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)