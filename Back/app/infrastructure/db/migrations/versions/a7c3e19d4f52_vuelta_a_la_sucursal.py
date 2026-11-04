"""vuelta a la sucursal como opción de cada recorrido

Revision ID: a7c3e19d4f52
Revises: e5b19c3a7d20
Create Date: 2026-10-29 15:00:00.000000

Antes dependía del tipo: los recorridos a domicilio volvían a la sucursal y los
de entre sucursales no. Ahora cada recorrido lo elige. Los que ya existían
conservan lo que tenían según su tipo.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a7c3e19d4f52'
down_revision: str | None = 'e5b19c3a7d20'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('recorridos') as batch_op:
        batch_op.add_column(sa.Column('vuelve_a_sucursal', sa.Boolean(), server_default='0', nullable=False))
    op.execute("UPDATE recorridos SET vuelve_a_sucursal = (tipo_distancia = 'CORTA')")


def downgrade() -> None:
    with op.batch_alter_table('recorridos') as batch_op:
        batch_op.drop_column('vuelve_a_sucursal')
