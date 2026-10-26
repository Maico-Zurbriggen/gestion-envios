"""HU11/HU12: constancias idempotentes y avisos de visita por email.

Revision ID: d2a6f81112ac
Revises: b7d41e9a2c63
"""

import sqlalchemy as sa
from alembic import op

revision = "d2a6f81112ac"
down_revision = "b7d41e9a2c63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("eventos_entrega") as tabla:
        tabla.add_column(sa.Column("operacion_id", sa.Uuid(), nullable=True))
        tabla.add_column(sa.Column("solicitud_hash", sa.String(64), nullable=True))
        tabla.add_column(sa.Column("recorrido_id", sa.Uuid(), nullable=True))
        tabla.add_column(sa.Column("receptor_fecha_nacimiento", sa.Date(), nullable=True))
        tabla.create_foreign_key("fk_evento_entrega_recorrido", "recorridos", ["recorrido_id"], ["id"])
        tabla.create_unique_constraint("uq_evento_entrega_operacion", ["operacion_id"])
    with op.batch_alter_table("notificaciones_envio") as tabla:
        tabla.add_column(sa.Column("evento_entrega_id", sa.Uuid(), nullable=True))
        tabla.add_column(sa.Column("procesando_at", sa.DateTime(timezone=True), nullable=True))
        tabla.create_foreign_key("fk_notificacion_evento_entrega", "eventos_entrega", ["evento_entrega_id"], ["id"])
        tabla.create_unique_constraint("uq_notificacion_evento_canal", ["evento_entrega_id", "canal"])


def downgrade() -> None:
    with op.batch_alter_table("notificaciones_envio") as tabla:
        tabla.drop_constraint("uq_notificacion_evento_canal", type_="unique")
        tabla.drop_constraint("fk_notificacion_evento_entrega", type_="foreignkey")
        tabla.drop_column("procesando_at")
        tabla.drop_column("evento_entrega_id")
    with op.batch_alter_table("eventos_entrega") as tabla:
        tabla.drop_constraint("uq_evento_entrega_operacion", type_="unique")
        tabla.drop_constraint("fk_evento_entrega_recorrido", type_="foreignkey")
        tabla.drop_column("receptor_fecha_nacimiento")
        tabla.drop_column("recorrido_id")
        tabla.drop_column("solicitud_hash")
        tabla.drop_column("operacion_id")
