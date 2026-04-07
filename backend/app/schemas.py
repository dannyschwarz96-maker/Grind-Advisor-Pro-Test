from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2, max_length=120)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MeResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str

class BeanBase(BaseModel):
    name: str
    roaster: Optional[str] = None
    bean_type: Optional[str] = None
    origin: Optional[str] = None
    roast_level: str = "Mittel"
    cupping: Optional[str] = None

class BeanCreate(BeanBase):
    pass

class BeanUpdate(BeanBase):
    pass

class BeanOut(BeanBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ShotTimeSeries(BaseModel):
    time_axis: List[float] = []
    pressure: List[float] = []
    temperature: List[float] = []
    flow: List[float] = []
    weight: List[float] = []

class ShotCreate(BaseModel):
    bean_id: str
    grind: float
    actual_time: float
    target_time: Optional[float] = None
    dose: Optional[float] = None
    yield_g: Optional[float] = None
    machine: Optional[str] = None
    notes: Optional[str] = None
    date: Optional[datetime] = None
    timeseries: Optional[ShotTimeSeries] = None

class ShotOut(BaseModel):
    id: str
    bean_id: str
    grind: float
    actual_time: float
    target_time: Optional[float] = None
    dose: Optional[float] = None
    yield_g: Optional[float] = None
    machine: Optional[str] = None
    notes: Optional[str] = None
    date: datetime
    timeseries_json: Optional[dict] = None

    class Config:
        from_attributes = True

class PredictRequest(BaseModel):
    bean_id: str
    target_time: float = 27
    dose: Optional[float] = 18

class PredictResponse(BaseModel):
    grind: float
    grind_lo: Optional[float] = None
    grind_hi: Optional[float] = None
    confidence: float
    model_level: str
    n_samples: int
    explanation: str

class ImportParseRequest(BaseModel):
    raw_json: str

class ImportParseResponse(BaseModel):
    machine: str
    coffee: Optional[str]
    duration: float
    grind: Optional[float]
    dose: Optional[float]
    yield_g: Optional[float]
    date: Optional[str]
    notes: Optional[str]
    timeseries: dict
    features: dict
    errors: List[str] = []
