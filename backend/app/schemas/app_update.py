from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AppUpdateBase(BaseModel):
    title: str
    body: Optional[str] = None
    level: str = "info"  # info | warning | success | critical
    is_published: bool = False
    show_as_banner: bool = False
    banner_dismissible: bool = True
    show_on_public: bool = True
    link_url: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

class AppUpdateCreate(AppUpdateBase):
    pass

class AppUpdateUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    level: Optional[str] = None
    is_published: Optional[bool] = None
    show_as_banner: Optional[bool] = None
    banner_dismissible: Optional[bool] = None
    show_on_public: Optional[bool] = None
    link_url: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

class AppUpdateResponse(AppUpdateBase):
    id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
