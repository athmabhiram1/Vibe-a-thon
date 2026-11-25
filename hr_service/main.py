"""HR directory service — FastAPI(title="hr-directory"), port 8001."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hr_service.routers.hr import router as hr_router

app = FastAPI(title="hr-directory")

# Demo CORS: allow all origins so browsers opening frontend.html via file://
# (Origin: null preflights) succeed. Production would restrict origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", operation_id="hr_health_check", summary="Liveness probe")
async def hr_health_check() -> dict:
    """Liveness probe."""
    return {"ok": True}


# Routers included BEFORE any MCP wrap (no MCP mount in this service).
app.include_router(hr_router)

# uvicorn hr_service.main:app --port 8001
