"""La migración debe preservar las constancias previas de HU13 y poder revertirse."""

import sqlite3
import uuid

from alembic import command
from alembic.config import Config

from app.core.config import settings


def test_hu11_hu12_upgrade_downgrade_preserva_constancias(tmp_path, monkeypatch):
    ruta = tmp_path / "migracion.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{ruta.as_posix()}")
    monkeypatch.setattr(settings, "DATABASE_URL_MIGRACIONES", "")
    config = Config("alembic.ini")
    command.upgrade(config, "b7d41e9a2c63")
    id_evento = uuid.uuid4().hex
    with sqlite3.connect(ruta) as db:
        # Fila histórica previa a HU11/HU12 (las FKs no son el objeto de esta prueba).
        db.execute(
            "INSERT INTO eventos_entrega (id, paquete_id, tipo_evento, resultado, receptor_nombre, "
            "es_autorizado, documento_destinatario_verificado, usuario_registro_id, created_at) "
            "VALUES (?, ?, 'RETIRO_SUCURSAL', 'EXITOSO', 'Titular previo', 0, 1, ?, CURRENT_TIMESTAMP)",
            (id_evento, uuid.uuid4().hex, uuid.uuid4().hex),
        )
    command.upgrade(config, "d2a6f81112ac")
    with sqlite3.connect(ruta) as db:
        campos = {fila[1] for fila in db.execute("PRAGMA table_info(eventos_entrega)")}
        assert {"operacion_id", "solicitud_hash", "recorrido_id", "receptor_fecha_nacimiento"} <= campos
        fila = db.execute(
            "SELECT receptor_nombre, operacion_id FROM eventos_entrega WHERE id = ?", (id_evento,)
        ).fetchone()
        assert fila == ("Titular previo", None)
        campos_notif = {fila[1] for fila in db.execute("PRAGMA table_info(notificaciones_envio)")}
        assert {"evento_entrega_id", "procesando_at"} <= campos_notif
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "d2a6f81112ac"
    command.downgrade(config, "b7d41e9a2c63")
    with sqlite3.connect(ruta) as db:
        campos = {fila[1] for fila in db.execute("PRAGMA table_info(eventos_entrega)")}
        assert "operacion_id" not in campos
        assert (
            db.execute("SELECT receptor_nombre FROM eventos_entrega WHERE id = ?", (id_evento,)).fetchone()[0]
            == "Titular previo"
        )
    command.upgrade(config, "head")
