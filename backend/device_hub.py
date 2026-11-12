import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

from backend.database import get_connection, current_timestamp


class DeviceConnectionHub:
    """
    Manages live WebSocket connections from registered device nodes (PCs, laptops)
    and browser/mobile clients, enabling bidirectional remote command execution and real-time state sync.
    """

    def __init__(self):
        # device_id -> WebSocket connection
        self.active_devices: Dict[str, WebSocket] = {}
        # client_id -> WebSocket connection
        self.active_clients: Dict[str, WebSocket] = {}
        # command_id -> asyncio.Future for awaiting command execution results
        self.pending_commands: Dict[str, asyncio.Future] = {}
        # Lock for safe thread/task synchronization
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------
    # DEVICE WEBSOCKETS (Physical machines / Agents)
    # -------------------------------------------------------------

    async def connect_device(self, device_id: str, websocket: WebSocket, metadata: Optional[dict] = None):
        await websocket.accept()
        async with self._lock:
            self.active_devices[device_id] = websocket

        # Update database status to online
        self._update_device_status(device_id, "online")
        await self.broadcast_to_clients({
            "type": "device_status_changed",
            "device_id": device_id,
            "status": "online",
            "timestamp": current_timestamp()
        })
        print(f"DEVICE CONNECTED TO HUB: {device_id}")

    async def disconnect_device(self, device_id: str):
        async with self._lock:
            if device_id in self.active_devices:
                del self.active_devices[device_id]

        # Update database status to offline
        self._update_device_status(device_id, "offline")
        await self.broadcast_to_clients({
            "type": "device_status_changed",
            "device_id": device_id,
            "status": "offline",
            "timestamp": current_timestamp()
        })
        print(f"DEVICE DISCONNECTED FROM HUB: {device_id}")

    def is_device_online(self, device_id: str) -> bool:
        return device_id in self.active_devices

    # -------------------------------------------------------------
    # CLIENT WEBSOCKETS (Web / Mobile PWA users)
    # -------------------------------------------------------------

    async def connect_client(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_clients[client_id] = websocket
        print(f"CLIENT CONNECTED TO HUB: {client_id}")

    async def disconnect_client(self, client_id: str):
        async with self._lock:
            if client_id in self.active_clients:
                del self.active_clients[client_id]
        print(f"CLIENT DISCONNECTED FROM HUB: {client_id}")

    async def broadcast_to_clients(self, message: dict):
        dead_clients = []
        payload = json.dumps(message)
        for client_id, ws in list(self.active_clients.items()):
            try:
                await ws.send_text(payload)
            except Exception:
                dead_clients.append(client_id)

        if dead_clients:
            async with self._lock:
                for cid in dead_clients:
                    self.active_clients.pop(cid, None)

    # -------------------------------------------------------------
    # REMOTE COMMAND DISPATCH & AWAIT
    # -------------------------------------------------------------

    async def dispatch_command(
        self,
        user_id: str,
        target_device_id: str,
        action: str,
        parameters: dict,
        timeout: float = 15.0
    ) -> dict:
        """
        Dispatches a remote command to a target device node over its live WebSocket
        and asynchronously awaits the response.
        """
        command_id = str(uuid.uuid4())
        created_at = current_timestamp()

        # Check if device is connected
        ws = self.active_devices.get(target_device_id)
        if not ws:
            # Check device name in database
            device_info = self._get_device_from_db(target_device_id)
            dev_name = device_info["device_name"] if device_info else target_device_id
            return {
                "success": False,
                "command_id": command_id,
                "message": f"Device '{dev_name}' is currently offline. Please run the ZORIN device agent on that device to enable remote actions.",
                "offline": True
            }

        # Record command in database
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO remote_commands (command_id, user_id, target_device_id, action, parameters, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'dispatched', ?)
            """, (command_id, user_id, target_device_id, action, json.dumps(parameters), created_at))
            conn.commit()

        # Prepare future to wait for response
        future = asyncio.get_running_loop().create_future()
        self.pending_commands[command_id] = future

        # Send command message over WebSocket
        message_payload = {
            "type": "execute_command",
            "command_id": command_id,
            "action": action,
            "parameters": parameters,
            "timestamp": created_at
        }

        try:
            await ws.send_text(json.dumps(message_payload))
            print(f"COMMAND DISPATCHED: {action} -> {target_device_id} (ID: {command_id})")

            # Await device response with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            
            # Save completed result to DB
            with get_connection() as conn:
                conn.execute("""
                    UPDATE remote_commands
                    SET status = 'completed', result = ?, completed_at = ?
                    WHERE command_id = ?
                """, (json.dumps(result), current_timestamp(), command_id))
                conn.commit()

            return result

        except asyncio.TimeoutError:
            error_result = {
                "success": False,
                "command_id": command_id,
                "message": f"Execution timed out after {timeout} seconds on target device.",
                "timeout": True
            }
            with get_connection() as conn:
                conn.execute("""
                    UPDATE remote_commands
                    SET status = 'timeout', result = ?, completed_at = ?
                    WHERE command_id = ?
                """, (json.dumps(error_result), current_timestamp(), command_id))
                conn.commit()
            return error_result

        except Exception as err:
            error_result = {
                "success": False,
                "command_id": command_id,
                "message": f"Failed to dispatch command to device: {err}"
            }
            return error_result

        finally:
            self.pending_commands.pop(command_id, None)

    def handle_command_result(self, command_id: str, result_data: dict):
        """Called when a device WebSocket sends back the result of a dispatched command."""
        future = self.pending_commands.get(command_id)
        if future and not future.done():
            future.set_result(result_data)

    # -------------------------------------------------------------
    # DATABASE HELPERS
    # -------------------------------------------------------------

    def _update_device_status(self, device_id: str, status: str):
        try:
            with get_connection() as conn:
                conn.execute("""
                    UPDATE devices
                    SET status = ?, last_seen = ?
                    WHERE device_id = ?
                """, (status, current_timestamp(), device_id))
                conn.commit()
        except Exception as e:
            print(f"Error updating device status: {e}")

    def _get_device_from_db(self, device_id: str) -> Optional[dict]:
        try:
            with get_connection() as conn:
                row = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
                return dict(row) if row else None
        except Exception:
            return None


# Global singleton instance of the hub
device_hub = DeviceConnectionHub()
