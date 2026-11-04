"""sucursales por usuario y sucursales activas

Revision ID: e5b19c3a7d20
Revises: c41a7e9d2b55
Create Date: 2026-10-28 16:30:00.000000

Cada usuario del personal trabaja en las sucursales que tiene habilitadas
(el Superadministrador, en todas). Para no dejar a nadie sin acceso, los
usuarios que ya existían quedan habilitados en todas las sucursales: después
el Superadministrador los restringe desde Usuarios.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5b19c3a7d20'
down_revision: str | None = 'c41a7e9d2b55'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('sucursales') as batch_op:
        batch_op.add_column(sa.Column('activa', sa.Boolean(), server_default=sa.true(), nullable=False))

    op.create_table(
        'usuario_sucursales',
        sa.Column('usuario_id', sa.Uuid(), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('sucursal_id', sa.Integer(), sa.ForeignKey('sucursales.id', ondelete='CASCADE'), primary_key=True),
    )

    # Vendedores y administrativos existentes: todas las sucursales. Repartidores: su sucursal base.
    op.execute(
        """
        INSERT INTO usuario_sucursales (usuario_id, sucursal_id)
        SELECT u.id, s.id FROM usuarios u CROSS JOIN sucursales s WHERE u.rol_id IN (2, 3)
        """
    )
    op.execute(
        """
        INSERT INTO usuario_sucursales (usuario_id, sucursal_id)
        SELECT r.usuario_id, r.sucursal_base_id FROM repartidores r WHERE r.sucursal_base_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_table('usuario_sucursales')
    with op.batch_alter_table('sucursales') as batch_op:
        batch_op.drop_column('activa')
