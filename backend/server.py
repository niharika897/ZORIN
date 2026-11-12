from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.database import initialize_database
from backend.device_registry import (
    register_device,
    get_device,
    get_all_devices,
    update_device_status
)


class DeviceRegistration(BaseModel):
    device_id: str
    device_name: str
    operating_system: str
    architecture: str = ""
    client_type: str = "desktop"
    capabilities: list[str] = Field(default_factory=list)


class DeviceStatusUpdate(BaseModel):
    status: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="ZORIN Shared Backend",
    description="Device registration and synchronization API",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "success": True,
        "assistant": "ZORIN",
        "message": "ZORIN backend is running."
    }


@app.get("/health")
async def health():
    return {
        "success": True,
        "status": "healthy"
    }


@app.post("/devices/register")
async def register_new_device(device: DeviceRegistration):

    try:
        result = register_device(
            device.model_dump()
        )

        return {
            "success": True,
            "message": "Device registered successfully.",
            "device": result
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.get("/devices")
async def list_devices():

    devices = get_all_devices()

    return {
        "success": True,
        "count": len(devices),
        "devices": devices
    }


@app.get("/devices/{device_id}")
async def retrieve_device(device_id: str):

    device = get_device(device_id)

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found."
        )

    return {
        "success": True,
        "device": device
    }


@app.patch("/devices/{device_id}/status")
async def change_device_status(
    device_id: str,
    update: DeviceStatusUpdate
):

    try:
        updated = update_device_status(
            device_id,
            update.status
        )

        if not updated:
            raise HTTPException(
                status_code=404,
                detail="Device not found."
            )

        return {
            "success": True,
            "message": "Device status updated.",
            "device": get_device(device_id)
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )