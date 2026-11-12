import os
import json
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.database import initialize_database, get_connection, current_timestamp
from backend.auth import (
    register_user,
    authenticate_user,
    get_current_user,
    decode_token,
    get_user_by_id,
    get_user_by_email,
)
from backend.device_registry import (
    register_device,
    get_device,
    get_all_devices,
    get_user_devices,
    set_default_device,
    update_device_status,
    delete_device,
)
from backend.device_hub import device_hub
from backend.assistant_service import assistant_service
from backend.memory_service import central_memory_service, CoreMemoryProtectedError


# -------------------------------------------------------------
# PYDANTIC SCHEMAS
# -------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""
    voice_preference: str = "Aoede"


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserSettingsUpdate(BaseModel):
    display_name: Optional[str] = None
    voice_preference: Optional[str] = None
    theme: Optional[str] = None


class DeviceRegistration(BaseModel):
    device_id: str
    device_name: str
    operating_system: str
    architecture: str = ""
    client_type: str = "desktop"
    capabilities: list[str] = Field(default_factory=list)


class DeviceStatusUpdate(BaseModel):
    status: str


class CommandDispatchRequest(BaseModel):
    action: str
    parameters: dict = Field(default_factory=dict)
    timeout: float = 15.0


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    target_device: Optional[str] = None


class MemoryCreateRequest(BaseModel):
    category: str = "general"
    content: str
    importance: int = 1
    is_core: bool = False


class MemoryUpdateRequest(BaseModel):
    content: str


class ConversationCreateRequest(BaseModel):
    title: str = "New Conversation"
    device_id: Optional[str] = None


class MessageCreateRequest(BaseModel):
    role: str
    content: str
    device_id: Optional[str] = None


# -------------------------------------------------------------
# LIFESPAN & APPLICATION SETUP
# -------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    print("ZORIN CENTRAL MULTI-DEVICE & UNIFIED MEMORY SERVER INITIALIZED.")
    yield


app = FastAPI(
    title="ZORIN Unified Brain & Multi-Device API",
    description="Central Persistent Memory & Multi-Device Synchronization Hub for ZORIN",
    version="2.1.0",
    lifespan=lifespan
)

# Enable CORS for all clients (Desktop, Android, Web, iOS, Tablets)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------
# AUTHENTICATION ROUTES
# -------------------------------------------------------------

@app.post("/api/auth/register")
async def api_register(data: UserRegisterRequest):
    try:
        result = register_user(
            email=data.email,
            password=data.password,
            display_name=data.display_name,
            voice_preference=data.voice_preference
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def api_login(data: UserLoginRequest):
    try:
        result = authenticate_user(
            email=data.email,
            password=data.password
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/api/auth/me")
async def api_get_me(current_user: dict = Depends(get_current_user)):
    return {"success": True, "user": current_user}


@app.patch("/api/auth/settings")
async def api_update_settings(
    update: UserSettingsUpdate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    fields = []
    values = []

    if update.display_name is not None:
        fields.append("display_name = ?")
        values.append(update.display_name.strip())
    if update.voice_preference is not None:
        fields.append("voice_preference = ?")
        values.append(update.voice_preference.strip())
    if update.theme is not None:
        fields.append("theme = ?")
        values.append(update.theme.strip())

    if fields:
        values.append(user_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?",
                tuple(values)
            )
            conn.commit()

    with get_connection() as conn:
        updated = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return {"success": True, "user": dict(updated)}


# -------------------------------------------------------------
# CENTRAL MEMORY ROUTES (All Clients Access & Update Here)
# -------------------------------------------------------------

@app.get("/api/memory")
async def list_memories(
    query: Optional[str] = None,
    core_only: bool = False,
    limit: int = 500,
    current_user: dict = Depends(get_current_user)
):
    uid = current_user["user_id"]
    if core_only:
        memories = central_memory_service.get_core_memories(uid, limit)
    elif query:
        memories = central_memory_service.search_memories(uid, query, limit)
    else:
        memories = central_memory_service.get_all_memories(uid, limit)

    return {
        "success": True,
        "count": len(memories),
        "memories": memories
    }


@app.post("/api/memory")
async def add_memory(
    req: MemoryCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        result = central_memory_service.save_memory(
            user_id=current_user["user_id"],
            category=req.category,
            content=req.content,
            importance=req.importance,
            is_core=req.is_core,
            source="explicit" if req.is_core else "conversation"
        )
        return {"success": True, "memory": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/memory/{memory_id}")
async def update_memory_endpoint(
    memory_id: int,
    req: MemoryUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    ok = central_memory_service.update_memory(
        user_id=current_user["user_id"],
        memory_id=memory_id,
        new_content=req.content
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found or not owned by user.")
    return {"success": True, "message": "Memory updated successfully."}


@app.patch("/api/memory/{memory_id}/pin")
async def pin_memory_endpoint(
    memory_id: int,
    current_user: dict = Depends(get_current_user)
):
    ok = central_memory_service.pin_memory(
        user_id=current_user["user_id"],
        memory_id=memory_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"success": True, "message": "Memory pinned to protected Core Memory."}


@app.patch("/api/memory/{memory_id}/unpin")
async def unpin_memory_endpoint(
    memory_id: int,
    current_user: dict = Depends(get_current_user)
):
    ok = central_memory_service.unpin_memory(
        user_id=current_user["user_id"],
        memory_id=memory_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"success": True, "message": "Memory unpinned to long-term memory."}


@app.delete("/api/memory/{memory_id}")
async def remove_memory(
    memory_id: int,
    allow_core: bool = False,
    current_user: dict = Depends(get_current_user)
):
    try:
        ok = central_memory_service.delete_memory(
            user_id=current_user["user_id"],
            memory_id=memory_id,
            allow_core=allow_core
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Memory not found.")
        return {"success": True, "message": "Memory deleted."}
    except CoreMemoryProtectedError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err)
        )


@app.get("/api/memory/context")
async def get_memory_context_endpoint(current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    return {
        "success": True,
        "persistent_context": central_memory_service.get_persistent_memory_context(uid),
        "conversation_context": central_memory_service.get_past_conversation_context(uid)
    }


# -------------------------------------------------------------
# CONVERSATIONS & HISTORY (Centralized across all devices)
# -------------------------------------------------------------

@app.get("/api/conversations")
async def get_conversations(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    convs = central_memory_service.get_conversations(current_user["user_id"], limit)
    return {"success": True, "conversations": convs}


@app.post("/api/conversations")
async def create_conversation_endpoint(
    req: ConversationCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    cid = central_memory_service.create_conversation(
        user_id=current_user["user_id"],
        title=req.title,
        device_id=req.device_id
    )
    return {"success": True, "conversation_id": cid}


@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    messages = central_memory_service.get_recent_messages(
        user_id=current_user["user_id"],
        conversation_id=conversation_id,
        limit=limit
    )
    return {"success": True, "messages": messages}


@app.post("/api/conversations/{conversation_id}/messages")
async def save_message_endpoint(
    conversation_id: int,
    req: MessageCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    central_memory_service.save_message(
        user_id=current_user["user_id"],
        conversation_id=conversation_id,
        role=req.role,
        content=req.content,
        device_id=req.device_id
    )
    return {"success": True, "message": "Message saved to central history."}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: int,
    current_user: dict = Depends(get_current_user)
):
    ok = central_memory_service.delete_conversation(
        user_id=current_user["user_id"],
        conversation_id=conversation_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"success": True, "message": "Conversation deleted."}


# -------------------------------------------------------------
# DEVICE MANAGEMENT ROUTES
# -------------------------------------------------------------

@app.post("/devices/register")
@app.post("/api/devices/register")
async def register_new_device(
    device: DeviceRegistration,
    current_user: dict = Depends(get_current_user)
):
    try:
        result = register_device(
            device.model_dump(),
            user_id=current_user["user_id"]
        )
        return {
            "success": True,
            "message": "Device registered and paired successfully.",
            "device": result
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/devices")
@app.get("/api/devices")
async def list_devices(current_user: dict = Depends(get_current_user)):
    devices = get_user_devices(current_user["user_id"])
    return {
        "success": True,
        "count": len(devices),
        "devices": devices
    }


@app.get("/devices/{device_id}")
@app.get("/api/devices/{device_id}")
async def retrieve_device(device_id: str, current_user: dict = Depends(get_current_user)):
    device = get_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return {"success": True, "device": device}


@app.post("/api/devices/{device_id}/default")
async def make_default_device(device_id: str, current_user: dict = Depends(get_current_user)):
    ok = set_default_device(current_user["user_id"], device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found or not owned by user.")
    return {"success": True, "message": "Default target device updated."}


@app.delete("/api/devices/{device_id}")
async def unpair_device(device_id: str, current_user: dict = Depends(get_current_user)):
    ok = delete_device(current_user["user_id"], device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found.")
    return {"success": True, "message": "Device unpaired successfully."}


@app.post("/api/devices/{device_id}/command")
async def dispatch_device_command(
    device_id: str,
    req: CommandDispatchRequest,
    current_user: dict = Depends(get_current_user)
):
    result = await device_hub.dispatch_command(
        user_id=current_user["user_id"],
        target_device_id=device_id,
        action=req.action,
        parameters=req.parameters,
        timeout=req.timeout
    )
    return {"success": result.get("success", False), "result": result}


# -------------------------------------------------------------
# ASSISTANT & CHAT CONVERSATION ROUTES
# -------------------------------------------------------------

@app.post("/api/assistant/chat")
async def assistant_chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    conv_id = req.conversation_id or f"session_{current_user['user_id'][:8]}"

    res = await assistant_service.chat(
        user_id=current_user["user_id"],
        user_profile=current_user,
        message=req.message.strip(),
        conversation_id=conv_id,
        origin_device_id=req.target_device
    )

    return {
        "success": res.get("success", True),
        "reply": res.get("text", ""),
        "tool_results": res.get("tool_results", []),
        "conversation_id": conv_id,
        "voice": current_user.get("voice_preference", "Aoede")
    }


# -------------------------------------------------------------
# SECURE WEBSOCKET CHANNELS: DEVICES & CLIENTS
# -------------------------------------------------------------

@app.websocket("/ws/device/{device_id}")
async def websocket_device_endpoint(
    websocket: WebSocket,
    device_id: str,
    token: Optional[str] = Query(None)
):
    """Persistent authenticated connection for remote PC / laptop agents."""
    # 1. Require a token for every device WebSocket connection
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
        return

    # 2. Reject invalid, expired, or malformed tokens with code 1008
    try:
        payload = decode_token(token)
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=f"Invalid or expired token: {e}")
        return

    # 3. Verify that the token belongs to an existing user
    user_id = payload.get("user_id")
    if not user_id or not get_user_by_id(user_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User does not exist")
        return

    # 4. Only call device_hub.connect_device after authentication succeeds
    await device_hub.connect_device(device_id, websocket)
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                msg_type = data.get("type")

                if msg_type == "command_result":
                    cmd_id = data.get("command_id")
                    result = data.get("result", {})
                    device_hub.handle_command_result(cmd_id, result)

                elif msg_type == "handshake":
                    identity = data.get("identity")
                    if identity:
                        try:
                            register_device(identity, user_id=user_id)
                        except Exception as e:
                            print(f"Error handling device handshake: {e}")

                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        await device_hub.disconnect_device(device_id)
    except Exception as err:
        print(f"Device WebSocket error for {device_id}: {err}")
        await device_hub.disconnect_device(device_id)


@app.websocket("/ws/client/{client_id}")
async def websocket_client_endpoint(
    websocket: WebSocket,
    client_id: str,
    token: Optional[str] = Query(None)
):
    """Real-time authenticated connection for web/mobile browsers."""
    user = None
    if token:
        try:
            payload = decode_token(token)
            user = get_user_by_id(payload.get("user_id"))
        except Exception:
            pass

    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return

    await device_hub.connect_client(client_id, websocket)
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await device_hub.disconnect_client(client_id)
    except Exception as err:
        print(f"Client WebSocket error for {client_id}: {err}")
        await device_hub.disconnect_client(client_id)


# -------------------------------------------------------------
# STATIC FILES & PWA FRONTEND
# -------------------------------------------------------------

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "success": True,
        "assistant": "ZORIN",
        "message": "ZORIN Multi-Device Backend is running."
    }


@app.get("/manifest.json")
async def serve_manifest():
    manifest_path = STATIC_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return JSONResponse(content={
        "name": "ZORIN AI",
        "short_name": "ZORIN",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0c14",
        "theme_color": "#00f3ff"
    })


@app.get("/service-worker.js")
async def serve_service_worker():
    sw_path = STATIC_DIR / "service-worker.js"
    if sw_path.exists():
        return FileResponse(sw_path, media_type="application/javascript")
    return JSONResponse(content={"status": "not_configured"}, status_code=404)


@app.get("/health")
async def health():
    return {
        "success": True,
        "status": "healthy",
        "active_devices": len(device_hub.active_devices),
        "active_clients": len(device_hub.active_clients),
        "timestamp": current_timestamp()
    }
