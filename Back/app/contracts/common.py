from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Modelo base para contratos Pydantic v2."""
    model_config = ConfigDict(populate_by_name=True)


class FieldError(BaseModel):
    """Representa un error en un campo específico según Adenda Sección C."""
    field: str
    message: str


class ErrorResponse(BaseModel):
    """Esquema estándar de respuestas de error según Adenda Sección C."""
    status: str = "error"
    code: str
    message: str
    errors: Optional[List[FieldError]] = None


class BaseSuccessResponse(BaseModel):
    """Esquema base de respuesta exitosa."""
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

