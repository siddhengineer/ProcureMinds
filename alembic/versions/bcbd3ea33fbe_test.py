
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'bcbd3ea33fbe'
down_revision: Union[str, None] = '5f129fc95f3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Ensure enum exists
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ruleitem_basis_enum') THEN
            CREATE TYPE ruleitem_basis_enum AS ENUM ('per_m3','per_m2','per_m','per_unit','absolute');
        END IF;
    END$$;
    """)

    # Add new enum value per_tile using AUTOCOMMIT (needed for PostgreSQL)
    conn = op.get_bind()
  

    # Columns (guarded)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='rule_items' AND column_name='category_id'
        ) THEN
            ALTER TABLE rule_items ADD COLUMN category_id INT NULL;
        END IF;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='rule_items' AND column_name='rate_basis'
        ) THEN
            ALTER TABLE rule_items ADD COLUMN rate_basis ruleitem_basis_enum NULL;
        END IF;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='rule_items' AND column_name='formula'
        ) THEN
            ALTER TABLE rule_items ADD COLUMN formula TEXT NULL;
        END IF;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='rule_items' AND column_name='resolved_rate'
        ) THEN
            ALTER TABLE rule_items ADD COLUMN resolved_rate NUMERIC NULL;
        END IF;
    END$$;
    """)

    # FK
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name='rule_items' AND constraint_name='fk_rule_items_category'
        ) THEN
            ALTER TABLE rule_items
            ADD CONSTRAINT fk_rule_items_category
            FOREIGN KEY (category_id) REFERENCES boq_categories(boq_category_id)
            ON DELETE SET NULL;
        END IF;
    END$$;
    """)

    # value nullable
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='rule_items' AND column_name='value' AND is_nullable='NO'
        ) THEN
            ALTER TABLE rule_items ALTER COLUMN value DROP NOT NULL;
        END IF;
    END$$;
    """)

    # Backfill (now per_tile is committed)
    op.execute("""
    UPDATE rule_items
    SET rate_basis = CASE
        WHEN unit LIKE '%_per_m3'   THEN 'per_m3'::ruleitem_basis_enum
        WHEN unit LIKE '%_per_m2'   THEN 'per_m2'::ruleitem_basis_enum
        WHEN unit LIKE '%_per_m'    THEN 'per_m'::ruleitem_basis_enum
        WHEN unit LIKE '%_per_tile' THEN 'per_tile'::ruleitem_basis_enum
        WHEN unit LIKE '%_per_unit' THEN 'per_unit'::ruleitem_basis_enum
        ELSE rate_basis
    END
    WHERE rate_basis IS NULL;
    """)

def downgrade():
    op.execute("ALTER TABLE rule_items DROP CONSTRAINT IF EXISTS fk_rule_items_category;")
    op.execute("ALTER TABLE rule_items DROP COLUMN IF EXISTS resolved_rate;")
    op.execute("ALTER TABLE rule_items DROP COLUMN IF EXISTS formula;")
    op.execute("ALTER TABLE rule_items DROP COLUMN IF EXISTS rate_basis;")
    op.execute("ALTER TABLE rule_items DROP COLUMN IF EXISTS category_id;")