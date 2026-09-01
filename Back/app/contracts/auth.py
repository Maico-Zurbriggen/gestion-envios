from uuid import UUID

from pydantic import Field, field_validator

from app.contracts.common import ApiModel


class LoginRequest(ApiModel):
    dni: str = Field(..., description="DNI del usuario (solo dígitos)", examples=["12345678"])
    password: str = Field(..., description="Contraseña del usuario", examples=["PasswordTemporal123!"])

    @field_validator("dni")
    @classmethod
    def validar_dni(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("El DNI debe contener solo dígitos.")
        if len(v) < 6 or len(v) > 20:
            raise ValueError("El DNI debe tener una longitud válida.")
        return v


class UserInfoResponse(ApiModel):
    id: UUID
    nombre: str
    dni: str
    email: str
    rol: str
    requiere_cambio_password: bool


class LoginNormalData(ApiModel):
    token: str
    user: UserInfoResponse


class LoginSuccessResponse(ApiModel):
    status: str = "success"
    data: LoginNormalData


class LoginTempTokenData(ApiModel):
    """`temp_token` tiene scope PASSWORD_RESET_ONLY: solo sirve para llamar
    a `/auth/cambiar-password` (HU02 Escenario 1), no para ningún otro
    endpoint protegido."""

    temp_token: str
    requiere_cambio_password: bool = True


class LoginRequiresPasswordChangeResponse(ApiModel):
    status: str = "requires_password_change"
    message: str = "Debe cambiar su contraseña temporal antes de continuar."
    data: LoginTempTokenData


# El login devuelve una u otra forma según si el usuario debe cambiar su
# contraseña temporal (HU02) o no; FastAPI documenta ambas en Swagger vía
# este Union.
LoginResponseUnion = LoginSuccessResponse | LoginRequiresPasswordChangeResponse


class CambiarPasswordRequest(ApiModel):
    password_actual: str = Field(..., description="Contraseña actual o temporal")
    nueva_password: str = Field(..., description="Nueva contraseña cumpliendo la política de seguridad")
    confirmacion_password: str = Field(..., description="Confirmación idéntica de la nueva contraseña")


class CambiarPasswordData(ApiModel):
    auth_token: str


class CambiarPasswordResponse(ApiModel):
    status: str = "success"
    message: str = "Contraseña actualizada exitosamente. Ya puede operar normalmente."
    data: CambiarPasswordData

