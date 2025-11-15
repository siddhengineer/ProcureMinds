from __future__ import annotations

from decimal import Decimal
from typing import Dict, Any, Tuple, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.validation_attempts import ValidationAttempt
from app.models.rule_set import RuleSet
from app.models.rule_item import RuleItem
from app.models.boq import BOQ
from app.models.boq_item import BOQItem
from app.models.boq_category import BOQCategory
from app.models.master_rule_item import MasterRuleItem
from app.models.master_rule_set import MasterRuleSet

# Reuse unit conversions from validation engine
try:
    from app.benchmarks.validation_engine import UNIT_TO_M
except Exception:
    UNIT_TO_M = {
        "m": Decimal("1"), "meter": Decimal("1"), "meters": Decimal("1"),
        "cm": Decimal("0.01"), "mm": Decimal("0.001"),
        "ft": Decimal("0.3048"), "foot": Decimal("0.3048"), "feet": Decimal("0.3048"),
        "in": Decimal("0.0254"), "inch": Decimal("0.0254"), "inches": Decimal("0.0254"),
    }


def _parse_unit_basis(unit: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Split a compound unit like 'bags_per_m3' into (unit, basis)."""
    if not unit:
        return None, None
    if "_per_" in unit:
        u, basis = unit.split("_per_", 1)
        return u, f"per_{basis}"
    return unit, None


def _rule_rate(
    rule: RuleItem,
    *,
    category_name: Optional[str],
    master_map: Dict[str, Dict[str, Dict[str, Optional[str]]]],
) -> Tuple[Optional[Decimal], Optional[str], Optional[str]]:
    """Return (rate_value, unit, basis) using rule fields or master defaults; parse unit if needed.

    We do NOT persist or require RuleItem.value. If missing, fall back to master default_value for the key.
    """
    # Prefer rule-provided unit/value when present; else fallback to master
    rate = Decimal(str(rule.value)) if rule.value is not None else None
    unit = rule.unit
    basis = rule.rate_basis

    if category_name and category_name in master_map:
        m = master_map[category_name].get(rule.key)
        if m:
            if rate is None and m.get("default_value") is not None:
                try:
                    rate = Decimal(str(m["default_value"]))
                except Exception:
                    rate = None
            if unit is None:
                unit = m.get("unit")

    if not basis:
        unit_only, parsed_basis = _parse_unit_basis(unit)
        unit = unit_only
        basis = parsed_basis
    return rate, unit, basis


def _to_m(val: Dict[str, Any]) -> Optional[Decimal]:
    try:
        v = Decimal(str(val["value"]))
        u = str(val["unit"]).lower().strip()
        return v * UNIT_TO_M[u]
    except Exception:
        return None


def _derive_metrics(payload: Dict[str, Any], rules: Dict[str, RuleItem]) -> Dict[str, Decimal]:
    metrics: Dict[str, Decimal] = {}
    rooms = payload.get("rooms") or []
    total_area = Decimal("0")
    for r in rooms:
        L = _to_m(r.get("length"))
        W = _to_m(r.get("width"))
        if L is not None and W is not None:
            total_area += (L * W)
    metrics["floor_area_m2"] = total_area

    # Slab volume if thickness provided via rules
    if "slab_thickness_m" in rules and rules["slab_thickness_m"].value is not None:
        thickness = Decimal(str(rules["slab_thickness_m"].value))
        metrics["slab_volume_m3"] = total_area * thickness
    return metrics


def _compute_items(
    db: Session,
    rules_by_key: Dict[str, RuleItem],
    key_category: Dict[str, Optional[str]],
    metrics: Dict[str, Decimal],
) -> List[BOQItem]:
    items: List[BOQItem] = []
    trace_common = {k: str(v) for k, v in metrics.items()}

    # Build master map: category -> key -> {unit, default_value}
    master_map: Dict[str, Dict[str, Dict[str, Optional[str]]]] = {}
    # Fetch all masters in one go
    masters = db.execute(select(MasterRuleItem, MasterRuleSet)
                         .join(MasterRuleSet, MasterRuleItem.master_rule_set_id == MasterRuleSet.master_rule_set_id)).all()
    for mi, ms in masters:
        # Need category name for mapping
        cat = db.get(BOQCategory, ms.category_id)
        if not cat:
            continue
        master_map.setdefault(cat.name, {})[mi.key] = {
            "unit": mi.unit,
            "default_value": mi.default_value,
        }

    def add_item(material_name: str, key: str, base_metric: str):
        rule = rules_by_key.get(key)
        if not rule:
            return
        category_name = key_category.get(key)
        rate, unit, basis = _rule_rate(rule, category_name=category_name, master_map=master_map)
        if rate is None or unit is None:
            return
        metric_val = metrics.get(base_metric)
        if metric_val is None:
            return
        qty = metric_val * rate
        item = BOQItem(
            material_name=material_name,
            rule_item_id=rule.rule_item_id,
            category_id=rule.category_id,
            quantity=qty,
            unit=unit,
            quantity_basis="absolute",
            notes=None,
            calculation_trace=str({
                **trace_common,
                "metric": base_metric,
                "metric_value": str(metric_val),
                "rate_key": key,
                "rate": str(rate),
                "unit": unit,
            }),
        )
        items.append(item)

    # Cement/Concrete related (use slab volume if present)
    if metrics.get("slab_volume_m3") is not None:
        add_item("Cement (bags)", "cement_bags_per_m3", "slab_volume_m3")
        add_item("Fine Sand (m3)", "sand_m3_per_m3", "slab_volume_m3")
        add_item("Coarse Aggregate (m3)", "aggregate_m3_per_m3", "slab_volume_m3")
        add_item("Steel (kg)", "steel_kg_per_m3", "slab_volume_m3")
        add_item("Shuttering (m2)", "shuttering_m2_per_m3", "slab_volume_m3")
        add_item("Admixture (L)", "admixture_L_per_m3", "slab_volume_m3")

    # Flooring adhesive/grout over floor area
    if metrics.get("floor_area_m2") is not None:
        add_item("Tile Adhesive (kg)", "adhesive_kg_per_m2", "floor_area_m2")
        add_item("Tile Grout (kg)", "grout_kg_per_m2", "floor_area_m2")

    return items


def compute_boq(
    db: Session,
    *,
    user_id: int,
    project_id: int,
    validation_attempt_id: int,
    rule_set_id: int,
) -> Tuple[int, int]:
    """Create a BOQ from rules and geometry metrics. Returns (boq_id, items_created)."""
    attempt = db.get(ValidationAttempt, validation_attempt_id)
    if not attempt or attempt.user_id != user_id or attempt.project_id != project_id:
        raise ValueError("ValidationAttempt not found for user/project")
    if attempt.status != "valid":
        raise ValueError("ValidationAttempt is not valid")

    rs = db.get(RuleSet, rule_set_id)
    if not rs or rs.user_id != user_id or rs.project_id != project_id:
        raise ValueError("RuleSet not found for user/project")

    rules = db.execute(select(RuleItem).where(RuleItem.rule_set_id == rule_set_id)).scalars().all()
    rules_by_key: Dict[str, RuleItem] = {r.key: r for r in rules}
    # map key -> category name
    cat_names: Dict[int, str] = {c.boq_category_id: c.name for c in db.execute(select(BOQCategory)).scalars().all()}
    key_category: Dict[str, Optional[str]] = {r.key: cat_names.get(r.category_id) if r.category_id else None for r in rules}

    payload = attempt.extracted_payload or {}
    metrics = _derive_metrics(payload, rules_by_key)

    # Optionally store metrics on attempt for reuse
    attempt.derived_metrics = {k: str(v) for k, v in metrics.items()}

    items = _compute_items(db, rules_by_key, key_category, metrics)

    boq = BOQ(user_id=user_id, project_id=project_id, rule_set_id=rule_set_id, status="draft")
    db.add(boq)
    db.flush()

    for it in items:
        it.boq_id = boq.boq_id
        db.add(it)

    db.commit()
    return boq.boq_id, len(items)
