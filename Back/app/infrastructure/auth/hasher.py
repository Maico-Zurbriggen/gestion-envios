import bcrypt
from app.core.config import settings


class HasherContrasenas:
    """Manejador de hashing y verificación de contraseñas con BCrypt."""

    @staticmethod
    def generar_hash(password: str) -> str:
        """Genera un hash BCrypt seguro utilizando el número de salt rounds configurado."""
        salt = bcrypt.gensalt(rounds=settings.BCRYPT_SALT_ROUNDS)
        hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed_bytes.decode("utf-8")

    @staticmethod
    def verificar_password(password_plana: str, password_hasheada: str) -> bool:
        """Verifica una contraseña en texto plano contra su hash almacenado."""
        try:
            return bcrypt.checkpw(
                password_plana.encode("utf-8"),
                password_hasheada.encode("utf-8"),
            )
        except Exception:
            return False

