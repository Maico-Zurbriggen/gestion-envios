import re
from datetime import timedelta

from pydantic import Field, field_validator
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
    DATABASE_URL_MIGRACIONES: str = ""
    """Opcional: endpoint directo de Neon para Alembic. Vacío: se deriva de DATABASE_URL quitando `-pooler`."""
    DB_ACTUALIZAR_ESQUEMA_AL_INICIAR: bool = True
    """Aplica `alembic upgrade head` al arrancar la API, para que la base compartida nunca quede atrás."""

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

    # Notificaciones y Proveedor de Email (HU05)
    EMAIL_PROVIDER: str = "mock"  # "mock" | "smtp" | "gmail"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = ""
    """Vacío: se usa `SMTP_USER`. Gmail reescribe el remitente si no coincide con la cuenta autenticada."""
    SMTP_FROM_NAME: str = "Sistema de Gestión de Envíos"
    SMTP_TIMEOUT_SEGUNDOS: int = 15
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # Circuito logístico (valores de referencia del mercado: Correo Argentino, Andreani, OCA)
    MAX_VISITAS_DOMICILIO: int = 2
    """Visitas a domicilio antes de dejar el paquete para retiro en sucursal."""
    PLAZO_RETIRO_DIAS_HABILES: int = 7
    """Días hábiles que un paquete espera en la sucursal antes de volver al remitente."""
    VENCIMIENTO_PRE_REGISTRO_DIAS: int = 10
    """Días para entregar en una sucursal un envío registrado online."""
    INTERVALO_PLAZOS_MINUTOS: int = 30
    """Cada cuánto se revisan los plazos vencidos (0 desactiva la revisión automática)."""

    # Notificaciones por WhatsApp (HU05 y aviso de visita de HU12)
    WHATSAPP_PROVIDER: str = "mock"  # "mock" | "meta" | "twilio" | "deshabilitado"
    WHATSAPP_CODIGO_PAIS: str = "54"
    WHATSAPP_TIMEOUT_SEGUNDOS: int = 15
    # Meta WhatsApp Cloud API
    WHATSAPP_META_TOKEN: str = ""
    WHATSAPP_META_PHONE_NUMBER_ID: str = ""
    WHATSAPP_META_API_VERSION: str = "v21.0"
    WHATSAPP_META_IDIOMA_PLANTILLA: str = "es_AR"
    WHATSAPP_META_PLANTILLA_NUEVO_ENVIO: str = ""
    WHATSAPP_META_PLANTILLA_VISITA_FALLIDA: str = ""
    WHATSAPP_META_PLANTILLA_AVISO_ESTADO: str = ""
    """Plantilla aprobada con 3 parámetros: nombre, novedad del envío y enlace."""
    WHATSAPP_META_DESTINATARIOS_PRUEBA: dict[str, str] = Field(default_factory=dict)
    """Equivalencias explícitas entre E.164 y el número guardado en la lista de prueba de Meta."""
    # Twilio (sandbox o remitente aprobado)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"
    TWILIO_CONTENT_SID_NUEVO_ENVIO: str = ""
    TWILIO_CONTENT_SID_VISITA_FALLIDA: str = ""
    TWILIO_CONTENT_SID_AVISO_ESTADO: str = ""

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

