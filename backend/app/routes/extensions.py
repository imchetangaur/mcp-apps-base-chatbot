"""Extension routes — MCP server management."""

from fastapi import APIRouter, HTTPException

from app.models.extensions import ExtensionConfig, ToolInfo
from app.services.mcp_manager import mcp_manager
from app.services.session_manager import session_manager

router = APIRouter(prefix="/api/sessions", tags=["extensions"])


@router.post("/{session_id}/extensions")
async def add_extension(session_id: str, config: ExtensionConfig):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        tools = await mcp_manager.add_extension(session_id, config)
        if config.name not in session.extension_names:
            session.extension_names.append(config.name)
        return {"status": "connected", "tools_discovered": len(tools)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}/extensions/{name}")
async def remove_extension(session_id: str, name: str):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await mcp_manager.remove_extension(session_id, name)
    session.extension_names = [n for n in session.extension_names if n != name]
    return {"status": "removed"}


@router.get("/{session_id}/extensions")
async def list_extensions(session_id: str):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    configs = await mcp_manager.get_extensions(session_id)
    return configs


@router.get("/{session_id}/tools", response_model=list[ToolInfo])
async def list_tools(session_id: str):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return await mcp_manager.list_tools(session_id)
