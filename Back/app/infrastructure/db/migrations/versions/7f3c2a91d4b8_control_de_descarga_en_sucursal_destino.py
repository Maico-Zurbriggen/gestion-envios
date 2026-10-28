"""control de descarga en sucursal de destino

Revision ID: 7f3c2a91d4b8
Revises: 539e81c168e2
Create Date: 2026-10-28 11:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7f3c2a91d4b8'
down_revision: str | None = '539e81c168e2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'controles_descarga',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('recorrido_id', sa.Uuid(), nullable=False),
        sa.Column('sucursal_id', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(length=10), nullable=False),
        sa.Column('iniciado_por_id', sa.Uuid(), nullable=False),
        sa.Column('cerrado_por_id', sa.Uuid(), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cerrado_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("estado IN ('EN_CURSO', 'CERRADO')", name='ck_controles_descarga_estado'),
        sa.ForeignKeyConstraint(['cerrado_por_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['iniciado_por_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['recorrido_id'], ['recorridos.id']),
        sa.ForeignKeyConstraint(['sucursal_id'], ['sucursales.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recorrido_id', 'sucursal_id', name='uq_control_descarga_recorrido_sucursal'),
    )
    op.create_table(
        'lecturas_descarga',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('control_id', sa.Uuid(), nullable=False),
        sa.Column('paquete_id', sa.Uuid(), nullable=True),
        sa.Column('codigo', sa.String(length=30), nullable=False),
        sa.Column('resultado', sa.String(length=12), nullable=False),
        sa.Column('detalle', sa.String(length=255), nullable=True),
        sa.Column('usuario_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "resultado IN ('CORRECTO', 'SOBRANTE', 'DESCONOCIDO')", name='ck_lecturas_descarga_resultado'
        ),
        sa.ForeignKeyConstraint(['control_id'], ['controles_descarga.id']),
        sa.ForeignKeyConstraint(['paquete_id'], ['paquetes.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('control_id', 'codigo', name='uq_lectura_descarga_control_codigo'),
    )
    op.create_index('ix_lecturas_descarga_control_id', 'lecturas_descarga', ['control_id'])


def downgrade() -> None:
    op.drop_index('ix_lecturas_descarga_control_id', table_name='lecturas_descarga')
    op.drop_table('lecturas_descarga')
    op.drop_table('controles_descarga')
