from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import sessions, chat, extensions, mcp_proxy, refine
from app.services.mcp_manager import mcp_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown: clean up all MCP connections
    await mcp_manager.cleanup_all()


app = FastAPI(title="HAI MCP-UI POC", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(extensions.router)
app.include_router(mcp_proxy.router)
app.include_router(refine.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
