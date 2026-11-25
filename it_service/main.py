# it_service/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from it_service.routers.it import router as it_router
from it_service.routers.live_moment import router as live_moment_router

app = FastAPI(title="ticketing-sla")

# Demo CORS: allow all origins so browsers opening frontend.html via file://
# (Origin: null preflights) succeed. Production would restrict origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", operation_id="it_health_check", summary="Liveness probe")
def it_health_check() -> dict:
    """Liveness probe."""
    return {"ok": True}


app.include_router(it_router)  # must precede any Synapse/MCP mount
app.include_router(live_moment_router)  # L1 live-discover: GET /it/oncall-coverage

# uvicorn it_service.main:app --port 8002
