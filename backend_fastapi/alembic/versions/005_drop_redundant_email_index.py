"""Drop redundant index on users.email

Revision ID: 005
Revises: 004
Create Date: 2026-07-20

O model original declarava Column(unique=True, index=True), o que cria DOIS
indices sobre a mesma coluna: o indice implicito da UNIQUE CONSTRAINT
("users_email_key") e um indice btree comum extra ("ix_users_email"). O
segundo e redundante - a constraint unica ja cobre buscas por igualdade
com a mesma eficiencia. Achado durante a auditoria da Sprint 6
(SPRINT6_REPORT.md).
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")


def downgrade() -> None:
    op.create_index("ix_users_email", "users", ["email"], unique=False)
