from fastapi import APIRouter, Depends
from app.config import Settings
from app.dependencies import get_settings
from app.models.response_models import HealthResponse

router = APIRouter()

@router.get(
    "/",
    response_model=HealthResponse,
    summary="Health Check Checkpoint",
    description="Returns the current operational status, service name, and version of the backend app."
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Returns application name, version, and running state."""
    return HealthResponse(
        status="running",
        service=settings.APP_NAME,
        version=settings.APP_VERSION
    )
