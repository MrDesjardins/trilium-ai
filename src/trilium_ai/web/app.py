"""FastAPI web application for Trilium AI."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from trilium_ai.shared.config import get_config
from trilium_ai.web.api import router as api_router

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get configuration
config = get_config()

# Initialize FastAPI app
app = FastAPI(
    title="Trilium AI",
    description="RAG-powered semantic search for your Trilium notes",
    version="0.1.0",
)

# Set up templates and static files
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
STATIC_VERSION = str(int((BASE_DIR / "static" / "js" / "app.js").stat().st_mtime))

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Trilium AI",
            "static_version": STATIC_VERSION,
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # Get port and host from config
    host = config.web.host
    port = config.web.port

    logger.info(f"Starting Trilium AI web server on {host}:{port}")
    uvicorn.run(
        "trilium_ai.web.app:app",
        host=host,
        port=port,
        reload=False,
    )
