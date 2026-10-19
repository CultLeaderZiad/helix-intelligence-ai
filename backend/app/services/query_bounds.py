"""Service-level bounds, including callers that bypass FastAPI query validation."""
from fastapi import HTTPException

MAX_PAGE_SIZE = 100
MAX_OFFSET = 1_000_000


def pagination_bounds(page: int, page_size: int) -> tuple[int, int]:
    """Reject invalid values, cap positive page sizes, then validate the offset."""
    if type(page) is not int or type(page_size) is not int or page < 1 or page_size < 1:
        raise HTTPException(status_code=422, detail="Invalid pagination: page and page_size must be positive integers")
    page_size = min(page_size, MAX_PAGE_SIZE)
    offset = (page - 1) * page_size
    if offset > MAX_OFFSET:
        raise HTTPException(status_code=422, detail="Invalid pagination: offset at most 1000000")
    return offset, page_size
