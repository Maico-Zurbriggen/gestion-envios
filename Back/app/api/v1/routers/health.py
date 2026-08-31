from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(tags=["Salud"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check del servicio",
)
async def health_check():
    return HealthResponse(
        status="healthy",
        service="Sistema de Gestión de Envíos Backend",
    )

