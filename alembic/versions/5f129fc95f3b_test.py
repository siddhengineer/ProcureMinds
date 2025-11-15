from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5f129fc95f3b'
down_revision: Union[str, None] = 'a68f07bef6c0'
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

    # Extend enum with per_tile if missing
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname='ruleitem_basis_enum' AND e.enumlabel='per_tile'
        ) THEN
            ALTER TYPE ruleitem_basis_enum ADD VALUE 'per_tile';
        END IF;
    END$$;
    """)

    # Add missing columns (guard each)
    # category_id
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

    # rate_basis (enum)
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

    # formula
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

    # resolved_rate
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

    # FK for category_id (if not already)
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

    # Make value nullable (ignore if already)
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

    # Backfill rate_basis only now that column exists
    op.execute("""
    UPDATE rule_items
    SET rate_basis = CASE
        WHEN unit LIKE '%_per_m3'   THEN 'per_m3'::ruleitem_basis_enum
        WHEN unit LIKE '%_per_m2'   THEN 'per_m2'::ruleitem_basis_enum
        WHEN unit LIKE '%_per_m'    THEN 'per_m'::ruleitem_basis_enum
        WHEN unit LIKE '%_per_unit' THEN 'per_unit'::ruleitem_basis_enum
        ELSE rate_basis
    END
    WHERE rate_basis IS NULL;
    """)


def downgrade():
    # No enum value deletions (unsafe). Remove added columns & FK.
    op.execute("ALTER TABLE rule_items DROP CONSTRAINT IF EXISTS fk_rule_items_category;")
    op.execute("ALTER TABLE rule_items DROP COLUMN IF EXISTS resolved_rate;")
    op.execute("ALTER TABLE rule_items DROP COLUMN IF EXISTS formula;")
    op.execute("ALTER TABLE rule_items DROP COLUMN IF EXISTS rate_basis;")
    op.execute("ALTER TABLE rule_items DROP COLUMN IF EXISTS category_id;")