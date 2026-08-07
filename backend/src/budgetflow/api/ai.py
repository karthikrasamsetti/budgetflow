"""AI-related routes. Phase 0: provider listing for the UI switcher."""

from fastapi import APIRouter

from ..ai.factory import available_providers

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/providers")
async def list_providers():
    """Providers the UI can switch between, with configured/default flags."""
    return {"providers": available_providers()}
