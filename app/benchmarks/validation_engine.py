from typing import Dict, Any, List, Optional
from decimal import Decimal
import json
import re

import httpx
import google.generativeai as genai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.benchmarks.validation_attempts import save_validation_attempt


UNIT_TO_M = {
    "m": Decimal("1"), "meter": Decimal("1"), "meters": Decimal("1"),
    "cm": Decimal("0.01"), "mm": Decimal("0.001"),
    "ft": Decimal("0.3048"), "foot": Decimal("0.3048"), "feet": Decimal("0.3048"),
    "in": Decimal("0.0254"), "inch": Decimal("0.0254"), "inches": Decimal("0.0254"),
}


def _convert_dim(dim: Optional[Dict[str, Any]], *, required: bool, label: str, invalid_fields: List[str], missing_fields: List[str]):
    if dim is None:
        if required:
            missing_fields.append(label)
        return None
    try:
        value = Decimal(str(dim["value"]))
        unit = str(dim["unit"]).lower().strip()
        if unit not in UNIT_TO_M:
            raise ValueError("unit")
        return {"value": str(value), "unit": unit, "normalized_m": str(value * UNIT_TO_M[unit])}
    except Exception:
        invalid_fields.append(f"{label}.unit")
        return None


def _openrouter_chat(messages: List[Dict[str, str]], *, model: str, temperature: float = 0) -> str:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER API key missing (openrouter_api_key in .env)")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        # Optional but recommended headers
        "HTTP-Referer": "https://procureminds.local",
        "X-Title": "ProcureMinds Validation",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        # Encourage JSON-only output when supported
        "response_format": {"type": "json_object"},
    }
    # Simple retry loop for transient errors
    last_err = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            last_err = e
            if e.response.status_code in (429, 500, 502, 503, 504):
                # brief backoff
                # note: avoid time.sleep to keep this non-blocking in serverless contexts
                continue
            raise
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"OpenRouter request failed after retries: {last_err}")


def _gemini_chat(messages: List[Dict[str, str]], *, model: str, temperature: float = 0) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI API key missing (gemini_api_key in .env)")
    genai.configure(api_key=settings.gemini_api_key)
    # Combine system + user content for Gemini
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    user_parts = [m["content"] for m in messages if m.get("role") == "user"]
    system_instruction = "\n\n".join(system_parts).strip() if system_parts else None
    model_obj = genai.GenerativeModel(model_name=model, system_instruction=system_instruction)
    # Send as a single user content with both prompts to keep structure simple
    content = "\n\n".join(user_parts).strip()
    resp = model_obj.generate_content(content, generation_config={"temperature": temperature})
    return resp.text or ""


def _extract_json_block(text: str) -> Dict[str, Any]:
    # Try to extract a JSON code block or parse raw JSON
    match = re.search(r"```(?:json)?\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    raw = match.group(1) if match else text
    return json.loads(raw)


def run_validation(db: Session, *, user_id: int, project_id: Optional[int], raw_input_text: str) -> Dict[str, Any]:
    # Prompt the LLM to extract normalized structure
    sys_prompt = (
        "You extract building inputs. Return ONLY JSON. Schema: "
        "{ rooms: [ { name, length:{value,unit}, width:{value,unit}, height:{value,unit}, "
        "  wall_thickness:{value,unit}, relations:[{source,relation,target}] } ], "
        "  global_wall_thickness:{value,unit}|null, floor_height:{value,unit}|null } ."
        "Units examples: m, cm, mm, ft, in. Preserve user's original unit strings."
    )
    user_prompt = f"Input:\n{raw_input_text}"
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]
    # Provider selection: prefer OpenRouter if key present, else Gemini
    if settings.openrouter_api_key:
        content = _openrouter_chat(messages, model=settings.openrouter_model, temperature=0)
    elif settings.gemini_api_key:
        content = _gemini_chat(messages, model=settings.gemini_model, temperature=0)
    else:
        raise RuntimeError("No LLM provider configured: set OPENROUTER_API_KEY or GEMINI_API_KEY in .env")

    try:
        data: Dict[str, Any] = _extract_json_block(content)
    except Exception:
        data = {"rooms": [], "global_wall_thickness": None, "floor_height": None}

    missing_fields: List[str] = []
    invalid_fields: List[str] = []
    unit_warnings: List[str] = []

    # Require at least one room
    if not data.get("rooms"):
        missing_fields.append("rooms")

    is_valid = len(missing_fields) == 0 and len(invalid_fields) == 0
    status = "valid" if is_valid else ("invalid" if (missing_fields or invalid_fields) else "needs_more_info")

    attempt = save_validation_attempt(
        db,
        user_id=user_id,
        project_id=project_id,
        parent_attempt_id=None,
        status=status,
        raw_input_text=raw_input_text,
        extracted_payload=data or None,
        missing_fields=missing_fields or None,
        invalid_fields=invalid_fields or None,
        unit_warnings=unit_warnings or None,
    )

    return {
        "validation_attempt_id": attempt.validation_attempt_id,
        "status": status,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "unit_warnings": unit_warnings,
    }
