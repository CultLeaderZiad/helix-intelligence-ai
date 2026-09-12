from fastapi import APIRouter

router = APIRouter()

# Higgsfield has been removed as a media provider; its webhook handler was
# removed with it. This router is kept (rather than unmounted) so /api/webhooks
# stays a stable mount point for any future provider callback.
