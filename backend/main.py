from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file in project root
current_dir = Path(__file__).parent.parent  # Go up to project root
env_path = current_dir / ".env"
load_dotenv(env_path)

# Create FastAPI app
app = FastAPI(
    title="BookSpine Detector API",
    description="AI-powered book spine detection and analysis system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
project_root = Path(__file__).parent.parent
Path(project_root / "static/uploads").mkdir(parents=True, exist_ok=True)
Path(project_root / "static/crops").mkdir(parents=True, exist_ok=True)
Path(project_root / "static/results").mkdir(parents=True, exist_ok=True)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount frontend files
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main frontend page"""
    frontend_path = project_root / "frontend" / "index.html"
    with open(frontend_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/test", response_class=HTMLResponse)
async def test_upload():
    """Serve the test upload page"""
    test_path = project_root / "test_upload.html"
    with open(test_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "BookSpine Detector API is running"}

# Import API routes
try:
    from api.upload import router as upload_router
    from api.analyze import router as analyze_router
    from api.recommend import router as recommend_router
    from api.metadata import router as metadata_router
except ImportError:
    # If running from project root, try relative imports
    from backend.api.upload import router as upload_router
    from backend.api.analyze import router as analyze_router
    from backend.api.recommend import router as recommend_router
    from backend.api.metadata import router as metadata_router

# Include routers
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
app.include_router(analyze_router, prefix="/api/analyze", tags=["analyze"])
app.include_router(recommend_router, prefix="/api/recommend", tags=["recommend"])
app.include_router(metadata_router, prefix="/api/metadata", tags=["metadata"])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

