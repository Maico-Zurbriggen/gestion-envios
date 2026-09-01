import re
from datetime import timedelta

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_duration(duration_str: str) -> timedelta:
    """Parsea una cadena de duración (ej. '8h', '15m', '1d', '3600s') a timedelta."""
    match = re.match(r"^(\d+)\s*([smhd])$", duration_str.strip().lower())
    if not match:
        try:
            return timedelta(seconds=int(duration_str))
        except ValueError:
            return timedelta(hours=8)

    val, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return timedelta(seconds=val)
    elif unit == "m":
        return timedelta(minutes=val)
    elif unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    return timedelta(hours=8)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    PROJECT_NAME: str = "Sistema de Gestión de Envíos"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Base de Datos
    DATABASE_URL: str = "sqlite+aiosqlite:///./gestion_envios.db"

    # Seguridad / JWT
    JWT_SECRET: str = "super-secret-jwt-key-replace-in-production-min-32-chars-long!"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: str = "8h"
    JWT_TEMP_TOKEN_EXPIRATION: str = "15m"
    BCRYPT_SALT_ROUNDS: int = 12

    # Semilla Superadministrador (Adenda Sección A y D)
    SUPERADMIN_SEED_PASSWORD: str | None = "SuperAdmin2026!*"
    SUPERADMIN_SEED_DNI: str = "00000000"
    SUPERADMIN_SEED_EMAIL: str = "admin@empresa.com"
    SUPERADMIN_SEED_NOMBRE: str = "Admin General"
    SUPERADMIN_SEED_TELEFONO: str = "+5493564000000"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        """Acepta valores de entorno habituales además de booleanos estrictos."""
        if not isinstance(value, str):
            return value

        normalized_value = value.strip().lower()
        if normalized_value in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if normalized_value in {"0", "false", "no", "off", "release", "production"}:
            return False

        return value

    @property
    def jwt_expiration_timedelta(self) -> timedelta:
        return parse_duration(self.JWT_EXPIRATION)

    @property
    def jwt_temp_token_expiration_timedelta(self) -> timedelta:
        return parse_duration(self.JWT_TEMP_TOKEN_EXPIRATION)


settings = Settings()

