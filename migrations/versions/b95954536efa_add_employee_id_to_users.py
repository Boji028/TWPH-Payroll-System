"""Add employee_id to users for self-service login

Revision ID: b95954536efa
Revises: f67e3189278f
Create Date: 2026-07-22 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b95954536efa'
down_revision = 'f67e3189278f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('employee_id', sa.Integer(), nullable=True))
        batch_op.create_unique_constraint('uq_users_employee_id', ['employee_id'])
        batch_op.create_foreign_key(
            'fk_users_employee_id_employees', 'employees', ['employee_id'], ['id']
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_employee_id_employees', type_='foreignkey')
        batch_op.drop_constraint('uq_users_employee_id', type_='unique')
        batch_op.drop_column('employee_id')
