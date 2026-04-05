"""create initial tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('organization', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, default=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('threat_id', sa.String(), nullable=True),
        sa.Column('severity', sa.Enum('critical','high','medium','low','info', name='severitylevel'), nullable=False),
        sa.Column('status', sa.Enum('open','acknowledged','resolved','false_positive', name='alertstatus'), nullable=True),
        sa.Column('classification', sa.String(), nullable=False),
        sa.Column('source_ip', sa.String(), nullable=True),
        sa.Column('destination_ip', sa.String(), nullable=True),
        sa.Column('source_port', sa.Integer(), nullable=True),
        sa.Column('destination_port', sa.Integer(), nullable=True),
        sa.Column('protocol', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('acknowledged_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alerts_id', 'alerts', ['id'])
    op.create_index('ix_alerts_threat_id', 'alerts', ['threat_id'], unique=True)

    # subscriptions
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('plan', sa.Enum('free','starter','professional','enterprise', name='plantype'), nullable=True),
        sa.Column('status', sa.Enum('active','canceled','past_due','trialing', name='subscriptionstatus'), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),
        sa.Column('stripe_price_id', sa.String(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_subscriptions_id', 'subscriptions', ['id'])


def downgrade() -> None:
    op.drop_table('subscriptions')
    op.drop_table('alerts')
    op.drop_table('users')
    op.execute("DROP TYPE IF EXISTS severitylevel")
    op.execute("DROP TYPE IF EXISTS alertstatus")
    op.execute("DROP TYPE IF EXISTS plantype")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
