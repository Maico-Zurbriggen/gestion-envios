"""HU10: estimaciones y orientacion de calles en recorridos

Revision ID: b7d41e9a2c63
Revises: 5c87e509d4e7
Create Date: 2026-10-24 12:00:00.000000

Agrega a `recorridos` los datos que la generación automática de HU10 necesita
conservar (orientación de la cuadrícula de calles usada para medir distancias,
distancia y duración estimadas) y el índice por `paquete_id` de
`recorrido_paquetes` previsto en el plan de base de datos (sección 5), que
ahora se usa para saber si un paquete ya está en un recorrido activo.

Se usa `batch_alter_table` para que la migración también corra sobre SQLite,
que no soporta `ALTER TABLE ... DROP COLUMN` en todas sus versiones.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d41e9a2c63"
down_revision: str | None = "5c87e509d4e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("recorridos") as batch_op:
        batch_op.add_column(
            sa.Column("orientacion_calles_grados", sa.Float(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("distancia_estimada_km", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("duracion_estimada_min", sa.Integer(), nullable=True))

    op.create_index("idx_recorrido_paquetes_paquete", "recorrido_paquetes", ["paquete_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_recorrido_paquetes_paquete", table_name="recorrido_paquetes")

    with op.batch_alter_table("recorridos") as batch_op:
        batch_op.drop_column("duracion_estimada_min")
        batch_op.drop_column("distancia_estimada_km")
        batch_op.drop_column("orientacion_calles_grados")
