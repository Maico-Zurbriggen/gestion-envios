"""circuito logístico completo: origen, balanza, plazo de retiro, devolución y avisos por hito

Revision ID: c41a7e9d2b55
Revises: d2a6f81112ac
Create Date: 2026-10-28 14:30:00.000000

Se usa `batch_alter_table` para que la migración también corra sobre SQLite.
La sucursal de origen de los paquetes ya admitidos se completa con la primera
recepción registrada en su historial.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c41a7e9d2b55'
down_revision: str | None = 'd2a6f81112ac'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('paquetes') as batch_op:
        batch_op.add_column(sa.Column('sucursal_origen_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('peso_admision_kg', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('retiro_hasta', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('en_devolucion', sa.Boolean(), server_default='0', nullable=False))
        batch_op.create_foreign_key('fk_paquetes_sucursal_origen', 'sucursales', ['sucursal_origen_id'], ['id'])

    with op.batch_alter_table('notificaciones_envio') as batch_op:
        batch_op.add_column(sa.Column('tipo_aviso', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('paquete_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key('fk_notificaciones_envio_paquete', 'paquetes', ['paquete_id'], ['id'])

    op.execute(
        """
        UPDATE paquetes SET sucursal_origen_id = (
            SELECT h.sucursal_id FROM historial_estados_paquete h
            WHERE h.paquete_id = paquetes.id
              AND h.sucursal_id IS NOT NULL
              AND h.estado_nuevo IN ('EN_SUCURSAL_ORIGEN', 'LISTO_PARA_RETIRO')
            ORDER BY h.created_at
            LIMIT 1
        )
        WHERE sucursal_origen_id IS NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table('notificaciones_envio') as batch_op:
        batch_op.drop_constraint('fk_notificaciones_envio_paquete', type_='foreignkey')
        batch_op.drop_column('paquete_id')
        batch_op.drop_column('tipo_aviso')

    with op.batch_alter_table('paquetes') as batch_op:
        batch_op.drop_constraint('fk_paquetes_sucursal_origen', type_='foreignkey')
        batch_op.drop_column('en_devolucion')
        batch_op.drop_column('retiro_hasta')
        batch_op.drop_column('peso_admision_kg')
        batch_op.drop_column('sucursal_origen_id')
