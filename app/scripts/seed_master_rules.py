from decimal import Decimal
from typing import List, Tuple, Optional
from pathlib import Path
import sys, os

# Load .env from project root BEFORE reading env vars
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT / ".env")

# Ensure project root is on sys.path so `import app...` works
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session

# Try normal app session first
try:
    from app.core.database import SessionLocal
except Exception:
    # Fallback: build SessionLocal from env
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    engine = create_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

from app.models.boq_category import BOQCategory
from app.models.master_rule_set import MasterRuleSet
from app.models.master_rule_item import MasterRuleItem

# Categories: (name, description)
CATS: List[Tuple[str, str]] = [
    ("earthwork", "Earthwork related rules"),
    ("cement_concrete_work", "Concrete and RCC rules"),
    ("flooring", "Flooring and tiling rules"),
]

# Master rule sets:
# (set_code, set_description, category_name, items)
# items: (key, unit, description, default_value (Decimal|None), formula (str|None))
MASTER_SETS = [
    # Earthwork
    ("EW-EXC-TRENCH", "Foundation trench excavation", "earthwork", [
        ("excavation_swelling_factor", "multiplier", "Typical bulking/swelling factor", Decimal("1.20"), None),
        ("excavation_overbreak_allowance", "multiplier", "Allowance for overbreak", Decimal("1.05"), None),
        ("disposal_lead_m", "m", "Lead for disposal of excavated soil", Decimal("30"), None),
        ("max_depth_m", "m", "Typical depth limit for trench without shoring", Decimal("1.5"), None),
    ]),
    ("EW-BACKFILL-COMPACTION", "Backfilling and compaction", "earthwork", [
        ("backfill_layer_thickness_m", "m", "Layer thickness per pass", Decimal("0.20"), None),
        ("compaction_passes", "count", "No. of passes per layer", Decimal("4"), None),
        ("shrinkage_factor", "multiplier", "Shrinkage factor for compacted fill", Decimal("0.90"), None),
        ("moisture_content_percent", "%", "Optimum moisture content", Decimal("12"), None),
    ]),
    ("EW-GSB-LAYER", "Granular sub-base layer", "earthwork", [
        ("gsb_thickness_m", "m", "Design thickness", Decimal("0.15"), None),
        ("gsb_density_t_per_m3", "t_per_m3", "Material density", Decimal("1.90"), None),
        ("gsb_wastage_multiplier", "multiplier", "Wastage/handling", Decimal("1.03"), None),
    ]),
    # Cement concrete work
    ("CC-PCC-1-4-8", "Plain cement concrete 1:4:8", "cement_concrete_work", [
        ("pcc_thickness_m", "m", "PCC thickness", Decimal("0.10"), None),
        ("cement_bags_per_m3", "bags_per_m3", "Cement consumption", Decimal("5.0"), None),
        ("sand_m3_per_m3", "m3_per_m3", "Fine aggregate per m3", Decimal("0.44"), None),
        ("aggregate_m3_per_m3", "m3_per_m3", "Coarse aggregate per m3", Decimal("0.88"), None),
        ("pcc_wastage_multiplier", "multiplier", "Wastage/handling", Decimal("1.02"), None),
    ]),
    ("CC-RCC-SLAB-M20", "RCC slab M20", "cement_concrete_work", [
        ("slab_thickness_m", "m", "Slab thickness", Decimal("0.12"), None),
        ("cement_bags_per_m3", "bags_per_m3", "Cement consumption", Decimal("7.4"), None),
        ("sand_m3_per_m3", "m3_per_m3", "Fine aggregate per m3", Decimal("0.45"), None),
        ("aggregate_m3_per_m3", "m3_per_m3", "Coarse aggregate per m3", Decimal("0.90"), None),
        ("steel_kg_per_m3", "kg_per_m3", "Reinforcement density", Decimal("80"), None),
        ("shuttering_m2_per_m3", "m2_per_m3", "Formwork per m3", Decimal("8.5"), None),
        ("admixture_L_per_m3", "L_per_m3", "Plasticizer/admixture", Decimal("2.0"), None),
    ]),
    ("CC-RCC-BEAM-M20", "RCC beam M20", "cement_concrete_work", [
        ("steel_kg_per_m3", "kg_per_m3", "Reinforcement density", Decimal("110"), None),
        ("formwork_m2_per_m3", "m2_per_m3", "Formwork per m3", Decimal("16"), None),
        ("beam_wastage_multiplier", "multiplier", "Wastage/handling", Decimal("1.03"), None),
        ("concrete_m3_per_m_run", "m3_per_m", "Concrete per meter run (depends on section)", None, "beam_width_m * beam_depth_m"),
    ]),
    ("CC-COLUMN-M20", "RCC column M20", "cement_concrete_work", [
        ("steel_kg_per_m3", "kg_per_m3", "Reinforcement density", Decimal("120"), None),
        ("formwork_m2_per_m3", "m2_per_m3", "Formwork per m3", Decimal("14"), None),
        ("column_wastage_multiplier", "multiplier", "Wastage/handling", Decimal("1.03"), None),
        ("concrete_m3_per_column", "m3", "Concrete per column (depends on section)", None, "column_width_m * column_depth_m * clear_height_m"),
    ]),
    # Flooring
    ("FLR-SCREED-1-4", "Cement screed 1:4", "flooring", [
        ("screed_thickness_m", "m", "Screed thickness", Decimal("0.03"), None),
        ("cement_bags_per_m3", "bags_per_m3", "Cement consumption", Decimal("7.0"), None),
        ("sand_m3_per_m3", "m3_per_m3", "Fine aggregate per m3", Decimal("0.50"), None),
        ("screed_wastage_multiplier", "multiplier", "Wastage/handling", Decimal("1.05"), None),
    ]),
    ("FLR-TILE-600x600-VIT", "Vitrified floor tile 600x600", "flooring", [
        ("tile_size_m2", "m2_per_tile", "Tile area", Decimal("0.36"), None),
        ("tile_wastage_multiplier", "multiplier", "Wastage/cutting", Decimal("1.05"), None),
        ("adhesive_kg_per_m2", "kg_per_m2", "Tile adhesive", Decimal("4.0"), None),
        ("grout_kg_per_m2", "kg_per_m2", "Grout consumption", Decimal("0.5"), None),
    ]),
    ("FLR-SKIRT-100", "Tile skirting 100 mm", "flooring", [
        ("skirting_height_m", "m", "Skirting height", Decimal("0.10"), None),
        ("adhesive_kg_per_m2", "kg_per_m2", "Adhesive", Decimal("3.0"), None),
        ("grout_kg_per_m2", "kg_per_m2", "Grout", Decimal("0.4"), None),
        ("skirting_wastage_multiplier", "multiplier", "Wastage/cutting", Decimal("1.05"), None),
    ]),
]


def upsert_category(db: Session, name: str, description: Optional[str]) -> int:
    cat = db.query(BOQCategory).filter(BOQCategory.name == name).one_or_none()
    if not cat:
        cat = BOQCategory(name=name, description=description or "")
        db.add(cat)
        db.flush()
        print(f"[seed] + category: {name} -> id={cat.boq_category_id}")
    else:
        if description and (cat.description or "") != description:
            cat.description = description
            print(f"[seed] ~ category desc: {name}")
    return cat.boq_category_id


def upsert_master_rule_set(db: Session, name: str, category_id: int, description: Optional[str], version: int = 1) -> MasterRuleSet:
    rs = (
        db.query(MasterRuleSet)
        .filter(MasterRuleSet.name == name, MasterRuleSet.category_id == category_id, MasterRuleSet.version == version)
        .one_or_none()
    )
    if not rs:
        rs = MasterRuleSet(name=name, category_id=category_id, description=description, version=version, is_active=1)
        db.add(rs)
        db.flush()
        print(f"[seed] + master_rule_set: {name} (cat_id={category_id}) -> id={rs.master_rule_set_id}")
    else:
        updates = []
        if (rs.description or "") != (description or ""):
            rs.description = description
            updates.append("description")
        if rs.is_active != 1:
            rs.is_active = 1
            updates.append("is_active")
        if updates:
            print(f"[seed] ~ master_rule_set: {name} fields={updates}")
    return rs


def upsert_master_rule_item(
    db: Session,
    master_rule_set_id: int,
    key: str,
    unit: str,
    description: Optional[str],
    default_value: Optional[Decimal],
    formula: Optional[str],
) -> MasterRuleItem:
    it = (
        db.query(MasterRuleItem)
        .filter(MasterRuleItem.master_rule_set_id == master_rule_set_id, MasterRuleItem.key == key)
        .one_or_none()
    )
    if not it:
        it = MasterRuleItem(
            master_rule_set_id=master_rule_set_id,
            key=key,
            unit=unit,
            description=description,
            default_value=default_value,
            formula=formula,
        )
        db.add(it)
        print(f"[seed]   + item: {key} ({unit})")
    else:
        updates = []
        if it.unit != unit:
            it.unit = unit
            updates.append("unit")
        if (it.description or "") != (description or ""):
            it.description = description
            updates.append("description")
        # allow None default_value/formula
        if (it.default_value or None) != (default_value or None):
            it.default_value = default_value
            updates.append("default_value")
        if (it.formula or None) != (formula or None):
            it.formula = formula
            updates.append("formula")
        if updates:
            print(f"[seed]   ~ item: {key} fields={updates}")
    return it


def seed():
    with SessionLocal() as db:
        print("[seed] start")
        # categories
        cat_map = {}
        for name, desc in CATS:
            cat_id = upsert_category(db, name, desc)
            cat_map[name] = cat_id
        db.flush()

        # master sets + items
        total_sets = 0
        total_items = 0
        for set_code, set_desc, cat_name, items in MASTER_SETS:
            cat_id = cat_map[cat_name]
            rs = upsert_master_rule_set(db, set_code, cat_id, set_desc, version=1)
            total_sets += 1
            for key, unit, desc, default_value, formula in items:
                upsert_master_rule_item(db, rs.master_rule_set_id, key, unit, desc, default_value, formula)
                total_items += 1
        db.commit()
        print(f"[seed] done | sets={total_sets} items={total_items}")


if __name__ == "__main__":
    seed()