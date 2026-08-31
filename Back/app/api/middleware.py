from typing import Any, Dict, List
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.logging import logger
from app.domain.constants.error_codes import ErrorCodes


def registrar_manejadores_excepciones(app: FastAPI) -> None:
    """Registra los manejadores de excepciones globales con el formato estándar de la Adenda Sección C."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        content: Dict[str, Any] = {
            "status": "error",
            "code": exc.code,
            "message": exc.message,
        }
        if exc.errors is not None:
            content["errors"] = exc.errors

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errores_formateados: List[Dict[str, str]] = []
        for error in exc.errors():
            loc = error.get("loc", [])
            # Obtener el nombre del campo omitiendo 'body'
            campo = str(loc[-1]) if loc else "general"
            if campo == "body" and len(loc) > 1:
                campo = str(loc[1])
            
            msg = error.get("msg", "Dato inválido.")
            # Limpiar mensajes técnicos de pydantic para hacerlos legibles
            if msg.startswith("Value error, "):
                msg = msg.replace("Value error, ", "")
            
            errores_formateados.append({"field": campo, "message": msg})

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "code": ErrorCodes.VALIDATION_ERROR,
                "message": "Los datos proporcionados no son válidos.",
                "errors": errores_formateados,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = ErrorCodes.INTERNAL_ERROR
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            code = ErrorCodes.INVALID_TOKEN
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            code = ErrorCodes.FORBIDDEN_ACCESS
        elif exc.status_code == status.HTTP_404_NOT_FOUND:
            code = ErrorCodes.NOT_FOUND
        elif exc.status_code == status.HTTP_400_BAD_REQUEST:
            code = ErrorCodes.VALIDATION_ERROR
        elif exc.status_code == status.HTTP_409_CONFLICT:
            code = ErrorCodes.DUPLICATE_ENTRY

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "code": code,
                "message": str(exc.detail),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Error no controlado en {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": ErrorCodes.INTERNAL_ERROR,
                "message": "Ocurrió un error inesperado en el servidor.",
            },
        )

