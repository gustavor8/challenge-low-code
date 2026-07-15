from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class LoadCreate(BaseModel):
    sku: str = Field(..., description="Código de barras ou SKU da carga")
    name: Optional[str] = Field(None, description="Nome da mercadoria")
    weight: float = Field(..., gt=0, description="Peso da carga em kg")
    is_imo: bool = Field(False, description="Indica se é carga perigosa (IMO)")

class LoadOut(BaseModel):
    id: int
    sku: str
    name: Optional[str]
    weight: float
    is_imo: bool
    allocated_at: datetime

    class Config:
        from_attributes = True

class SlotOut(BaseModel):
    id: int
    aisle: int
    column: int
    level: int
    is_occupied: bool
    is_imo_restricted: bool
    load: Optional[LoadOut] = None

    class Config:
        from_attributes = True

class SuggestRequest(BaseModel):
    sku: str
    weight: float
    is_imo: bool

class SuggestResponse(BaseModel):
    slot_id: int
    aisle: int
    column: int
    level: int
    message: str

class ConfirmRequest(BaseModel):
    slot_id: int
    sku: str
    name: Optional[str] = None
    weight: float
    is_imo: bool

class OccupancyStats(BaseModel):
    total_slots: int
    occupied_slots: int
    occupancy_rate: float
    imo_slots: int
    occupied_imo_slots: int
    limit_height: int
