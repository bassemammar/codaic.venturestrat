"""Initial auth tables

Revision ID: 8ae3ad582f2c
Revises:
Create Date: 2026-02-20 20:14:55.809750

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8ae3ad582f2c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tables (FKs added separately via ALTER TABLE to avoid ordering issues)
    op.create_table('aut_permission',
    sa.Column('id', sa.String(length=255), nullable=True),
    sa.Column('resource', sa.String(length=100), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('service_name', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tenant_id', sa.String(length=36), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code'),
    schema='auth'
    )
    op.create_table('aut_role',
    sa.Column('id', sa.String(length=255), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('is_system', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tenant_id', sa.String(length=36), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code'),
    schema='auth'
    )
    op.create_table('aut_user',
    sa.Column('id', sa.String(length=255), nullable=True),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=True),
    sa.Column('last_name', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_login_count', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('default_tenant_id', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tenant_id', sa.String(length=36), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username'),
    schema='auth'
    )
    op.create_table('aut_session',
    sa.Column('id', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('refresh_token_hash', sa.String(length=255), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tenant_id', sa.String(length=36), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )
    op.create_table('aut_user_role',
    sa.Column('id', sa.String(length=255), nullable=True),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('role_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tenant_id', sa.String(length=36), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )

    # Indexes
    op.create_index(op.f('ix_auth_aut_permission_tenant_id'), 'aut_permission', ['tenant_id'], unique=False, schema='auth')
    op.create_index(op.f('ix_auth_aut_role_tenant_id'), 'aut_role', ['tenant_id'], unique=False, schema='auth')
    op.create_index(op.f('ix_auth_aut_session_tenant_id'), 'aut_session', ['tenant_id'], unique=False, schema='auth')
    op.create_index(op.f('ix_auth_aut_session_user_id'), 'aut_session', ['user_id'], unique=False, schema='auth')
    op.create_index(op.f('ix_auth_aut_user_tenant_id'), 'aut_user', ['tenant_id'], unique=False, schema='auth')
    op.create_index(op.f('ix_auth_aut_user_role_role_id'), 'aut_user_role', ['role_id'], unique=False, schema='auth')
    op.create_index(op.f('ix_auth_aut_user_role_tenant_id'), 'aut_user_role', ['tenant_id'], unique=False, schema='auth')
    op.create_index(op.f('ix_auth_aut_user_role_user_id'), 'aut_user_role', ['user_id'], unique=False, schema='auth')

    # Foreign keys (via ALTER TABLE to avoid cross-schema ordering issues)
    op.create_foreign_key('fk_aut_permission_tenant_id', 'aut_permission', 'tenants', ['tenant_id'], ['id'], source_schema='auth', referent_schema='registry', ondelete='RESTRICT')
    op.create_foreign_key('fk_aut_role_tenant_id', 'aut_role', 'tenants', ['tenant_id'], ['id'], source_schema='auth', referent_schema='registry', ondelete='RESTRICT')
    op.create_foreign_key('fk_aut_user_tenant_id', 'aut_user', 'tenants', ['tenant_id'], ['id'], source_schema='auth', referent_schema='registry', ondelete='RESTRICT')
    op.create_foreign_key('fk_aut_session_tenant_id', 'aut_session', 'tenants', ['tenant_id'], ['id'], source_schema='auth', referent_schema='registry', ondelete='RESTRICT')
    op.create_foreign_key('fk_aut_session_user_id', 'aut_session', 'aut_user', ['user_id'], ['id'], source_schema='auth', referent_schema='auth', ondelete='RESTRICT')
    op.create_foreign_key('fk_aut_user_role_role_id', 'aut_user_role', 'aut_role', ['role_id'], ['id'], source_schema='auth', referent_schema='auth', ondelete='RESTRICT')
    op.create_foreign_key('fk_aut_user_role_user_id', 'aut_user_role', 'aut_user', ['user_id'], ['id'], source_schema='auth', referent_schema='auth', ondelete='RESTRICT')
    op.create_foreign_key('fk_aut_user_role_tenant_id', 'aut_user_role', 'tenants', ['tenant_id'], ['id'], source_schema='auth', referent_schema='registry', ondelete='RESTRICT')


def downgrade() -> None:
    op.drop_index(op.f('ix_auth_aut_user_role_user_id'), table_name='aut_user_role', schema='auth')
    op.drop_index(op.f('ix_auth_aut_user_role_tenant_id'), table_name='aut_user_role', schema='auth')
    op.drop_index(op.f('ix_auth_aut_user_role_role_id'), table_name='aut_user_role', schema='auth')
    op.drop_table('aut_user_role', schema='auth')
    op.drop_index(op.f('ix_auth_aut_user_tenant_id'), table_name='aut_user', schema='auth')
    op.drop_table('aut_user', schema='auth')
    op.drop_index(op.f('ix_auth_aut_session_user_id'), table_name='aut_session', schema='auth')
    op.drop_index(op.f('ix_auth_aut_session_tenant_id'), table_name='aut_session', schema='auth')
    op.drop_table('aut_session', schema='auth')
    op.drop_index(op.f('ix_auth_aut_role_tenant_id'), table_name='aut_role', schema='auth')
    op.drop_table('aut_role', schema='auth')
    op.drop_index(op.f('ix_auth_aut_permission_tenant_id'), table_name='aut_permission', schema='auth')
    op.drop_table('aut_permission', schema='auth')
