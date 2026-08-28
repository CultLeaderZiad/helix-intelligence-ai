from pydantic import BaseModel, ConfigDict
from typing import TypeVar, Generic, List, Optional, Any

T = TypeVar('T')

class Paginated(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    has_more: bool
    took_ms: Optional[int] = None

class ServiceErrorShape(BaseModel):
    message: str
    status: Optional[int] = None
    code: str
