from typing import Dict, Any, List, Optional, Tuple
import json
import re

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.rule_set import RuleSet
from app.models.rule_item import RuleItem
from app.models.boq_category import BOQCategory
from app.models.validation_attempts import ValidationAttempt

# Reuse LLM helpers by importing from validation_engine
from app.services.validation_engine import _openrouter_chat, _gemini_chat


def _extract_json_block(text: str) -> Dict[str, Any]:
    match = re.search(r"```(?:json)?\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    raw = match.group(1) if match else text
    return json.loads(raw)


def _get_or_create_boq_category(db: Session, name: str) -> int:
    norm = name.strip()
    obj = db.query(BOQCategory).filter(BOQCategory.name.ilike(norm)).first()
    if obj:
        return obj.boq_category_id
    new_obj = BOQCategory(name=norm, description=None)
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return new_obj.boq_category_id


def _build_rules_prompt(extracted_payload: Dict[str, Any]) -> List[Dict[str, str]]:
    sys_prompt = (
        "You are a civil estimation assistant. Generate a rule set for earthwork, cement concrete work, and flooring (tilework).\n"
        "Return ONLY JSON. Schema: { rule_set: { name }, rules: [ { category, key, value?|formula?, unit?, description? } ] }.\n"
        "Rules guidance: constants use 'value' (numeric). Derived computations use 'formula' (simple arithmetic with variables).\n"
        "Variables permitted: total_floor_area_m2, total_room_volume_m3, total_wall_volume_m3, avg_wall_thickness_m, floor_height_m.\n"
        "If using bags conversion, include constants like 'cement_per_m3' with unit 'bags_per_m3'.\n"
        "Categories must be one of: earthwork, cement_concrete_work, flooring."
    )
    user_prompt = (
        "Context (extracted building input):\n" + json.dumps(extracted_payload, ensure_ascii=False)
    )
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]


def generate_ruleset(
    db: Session,
    *,
    user_id: int,
    project_id: int,
    validation_attempt_id: int,
    rule_set_name: str = "default",
    preview: bool = False,
) -> Tuple[int, int, Optional[List[Dict[str, Any]]]]:
    attempt = db.query(ValidationAttempt).filter(
        ValidationAttempt.validation_attempt_id == validation_attempt_id,
        ValidationAttempt.user_id == user_id,
    ).first()
    if not attempt or not attempt.extracted_payload:
        raise ValueError("Validation attempt not found or has no extracted payload")

    messages = _build_rules_prompt(attempt.extracted_payload)

    # Prefer OpenRouter; fallback to Gemini
    if settings.openrouter_api_key:
        content = _openrouter_chat(messages, model=settings.openrouter_model, temperature=0)
    elif settings.gemini_api_key:
        content = _gemini_chat(messages, model=settings.gemini_model, temperature=0)
    else:
        raise RuntimeError("No LLM provider configured: set OPENROUTER_API_KEY or GEMINI_API_KEY in .env")

    data = _extract_json_block(content)
    rules: List[Dict[str, Any]] = data.get("rules", [])

    # Persist RuleSet
    rs = RuleSet(rule_set_id=None, user_id=user_id, project_id=project_id, name=(data.get("rule_set", {}) or {}).get("name", rule_set_name))
    db.add(rs)
    db.commit()
    db.refresh(rs)

    created = 0
    items_preview: List[Dict[str, Any]] = []
    for r in rules:
        category_name = r.get("category") or ""
        if category_name:
            # normalize typical variants
            cn = category_name.strip().lower().replace(" ", "_")
            if cn in ("earthwork", "cement_concrete_work", "flooring"):
                category_id = _get_or_create_boq_category(db, cn)
            else:
                category_id = _get_or_create_boq_category(db, category_name)
        else:
            category_id = None

        key = r.get("key")
        unit = r.get("unit")
        description = r.get("description")
        value = r.get("value")
        formula = r.get("formula")

        if key is None or (value is None and formula is None):
            continue

        # collect preview item
        items_preview.append({
            "category": category_name or None,
            "key": str(key),
            "value": float(value) if isinstance(value, (int, float)) else value,
            "formula": str(formula) if formula is not None else None,
            "unit": str(unit) if unit is not None else None,
            "description": str(description) if description is not None else None,
        })

        item = RuleItem(
            rule_set_id=rs.rule_set_id,
            category_id=category_id,
            key=str(key),
            value=value if value is not None else 0,
            unit=str(unit) if unit is not None else None,
            description=str(description) if description is not None else None,
            formula=str(formula) if formula is not None else None,
        )
        db.add(item)
        created += 1

    db.commit()
    return rs.rule_set_id, created, (items_preview if preview else None)
