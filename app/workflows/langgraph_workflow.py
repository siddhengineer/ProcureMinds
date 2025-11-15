from typing import Any, Optional, TypedDict, Dict, List
import json
import re
import logging

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.benchmarks.validation_engine import run_validation, _openrouter_chat, _gemini_chat
from app.benchmarks.boq_compute import compute_boq
from app.models.master_rule_set import MasterRuleSet
from app.models.master_rule_item import MasterRuleItem
from app.models.boq_category import BOQCategory
from app.models.rule_set import RuleSet
from app.models.rule_item import RuleItem
from app.models.boq import BOQ
from app.models.boq_item import BOQItem
from app.models.validation_attempts import ValidationAttempt
from app.models.benchmarks import BenchmarkMaterial
from app.core.config import settings


# Logger setup (lightweight, respects Uvicorn if already configured)
logger = logging.getLogger("procureminds.workflow")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


class ValidationFlowState(TypedDict):
    user_id: int
    project_id: Optional[int]
    raw_input_text: str
    validation_result: dict[str, Any]
    # ruleset generation outputs
    rules_result: dict[str, Any]
    # compute outputs
    compute_result: dict[str, Any]


class WorkflowGraph:
    """Two-node LangGraph: input -> validation (persists to DB).

    Usage: instantiate with a DB session and call execute_validate(...).
    """

    def __init__(self, db: Session):
        self.db = db
        self.graph = self._build_graph()
        logger.info("WorkflowGraph initialized and compiled")

    async def input_node(self, state: ValidationFlowState) -> ValidationFlowState:
        """Pass-through input collection node."""
        logger.info(
            "Node[input]: start | user_id=%s project_id=%s raw_len=%s",
            state.get("user_id"), state.get("project_id"), len(state.get("raw_input_text") or ""),
        )
        logger.info("Node[input]: done (pass-through)")
        return state

    async def validation_node(self, state: ValidationFlowState) -> ValidationFlowState:
        """Validate input via LLM and persist ValidationAttempt."""
        logger.info("Node[validate]: start | using_openrouter=%s using_gemini=%s",
                    bool(settings.openrouter_api_key), bool(settings.gemini_api_key))
        try:
            result = run_validation(
                self.db,
                user_id=state["user_id"],
                project_id=state.get("project_id"),
                raw_input_text=state["raw_input_text"],
            )
            state["validation_result"] = result
            # Console log LLM output for validation
            print("[LLM VALIDATE OUTPUT]", result)
            logger.info(
                "Node[validate]: done | status=%s attempt_id=%s",
                result.get("status"), result.get("validation_attempt_id")
            )
            return state
        except Exception as e:
            # Do not raise — record an error status and let the workflow route to END
            logger.exception("Node[validate]: unexpected error during validation")
            state["validation_result"] = {"status": "error", "error": str(e)}
            return state

    def _build_graph(self) -> StateGraph:
        """Build the validation + ruleset generation workflow."""
        workflow = StateGraph(ValidationFlowState)

        workflow.add_node("input", self.input_node)
        workflow.add_node("validate", self.validation_node)
        workflow.add_node("select_rules", self.select_rules_from_master_node)
        workflow.add_node("compute_boq", self.compute_boq_node)
        workflow.add_node("assemble_raw", self.assemble_raw_node)

        workflow.set_entry_point("input")
        workflow.add_edge("input", "validate")

        def _route_from_validate(state: ValidationFlowState) -> str:
            status = state.get("validation_result", {}).get("status")
            logger.info("Route[validate]: status=%s -> %s", status, ("go" if status == "valid" else "stop"))
            return "go" if status == "valid" else "stop"

        workflow.add_conditional_edges(
            "validate",
            _route_from_validate,
            {
                "go": "select_rules",
                "stop": END,
            },
        )
        workflow.add_edge("select_rules", "compute_boq")
        workflow.add_edge("compute_boq", END)
        workflow.add_edge("compute_boq", "assemble_raw")
        workflow.add_edge("assemble_raw", END)

        return workflow.compile()
    

    async def execute_validate(self, *, user_id: int, project_id: Optional[int], raw_input_text: str) -> dict[str, Any]:
        """Execute validation flow and return validation result payload."""
        logger.info("Execute[validate]: start | user_id=%s project_id=%s", user_id, project_id)
        initial_state: ValidationFlowState = {
            "user_id": user_id,
            "project_id": project_id,
            "raw_input_text": raw_input_text,
            "validation_result": {},
            "rules_result": {},
            "compute_result": {},
        }
        result = await self.graph.ainvoke(initial_state)
        logger.info("Execute[validate]: done | status=%s", (result.get("validation_result") or {}).get("status"))
        return result["validation_result"]

    async def execute_validate_and_generate(
        self,
        *,
        user_id: int,
        project_id: Optional[int],
        raw_input_text: str,
    ) -> dict[str, Any]:
        """Execute validation then ruleset generation; returns both results."""
        logger.info("Execute[full]: start | user_id=%s project_id=%s", user_id, project_id)
        initial_state: ValidationFlowState = {
            "user_id": user_id,
            "project_id": project_id,
            "raw_input_text": raw_input_text,
            "validation_result": {},
            "rules_result": {},
            "compute_result": {},
        }
        result = await self.graph.ainvoke(initial_state)
        logger.info(
            "Execute[full]: done | v_status=%s rule_set_ids=%s boqs=%s",
            (result.get("validation_result") or {}).get("status"),
            (result.get("rules_result") or {}).get("rule_set_ids"),
            (result.get("compute_result") or {}).get("boqs"),
        )
        return {
            "validation_result": result.get("validation_result", {}),
            "rules_result": result.get("rules_result", {}),
            "compute_result": result.get("compute_result", {}),
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generic executor used by existing workflow route; runs full flow if possible."""
        user_id = input_data.get("user_id")
        project_id = input_data.get("project_id")
        raw_input_text = input_data.get("raw_input_text", "")

        initial_state: ValidationFlowState = {
            "user_id": user_id,
            "project_id": project_id,
            "raw_input_text": raw_input_text,
            "validation_result": {},
            "rules_result": {},
            "compute_result": {},
        }
        logger.info("Execute[generic]: start | user_id=%s project_id=%s", user_id, project_id)
        result = await self.graph.ainvoke(initial_state)
        logger.info(
            "Execute[generic]: done | v_status=%s rule_set_ids=%s boqs=%s",
            (result.get("validation_result") or {}).get("status"),
            (result.get("rules_result") or {}).get("rule_set_ids"),
            (result.get("compute_result") or {}).get("boqs"),
        )
        return {
            "validation_result": result.get("validation_result", {}),
            "rules_result": result.get("rules_result", {}),
        }

    def _parse_unit_basis(self, unit: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not unit:
            return None, None
        if "_per_" in unit:
            u, basis = unit.split("_per_", 1)
            return u, f"per_{basis}"
        return unit, None

    def _extract_json_block(self, text: str) -> Dict[str, Any]:
        match = re.search(r"```(?:json)?\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
        raw = match.group(1) if match else text
        try:
            return json.loads(raw)
        except Exception:
            return {"selected": []}

    async def select_rules_from_master_node(self, state: ValidationFlowState) -> ValidationFlowState:
        """Select applicable master rule sets using LLM classification, with deterministic fallback.

        - Prompts the LLM with extracted payload + catalog names to choose applicable sets.
        - Validates selections against the master catalog.
        - Persists a new `RuleSet` and clones corresponding `MasterRuleItem` rows into `RuleItem`.
        - Falls back to a safe default subset if LLM unavailable or returns nothing.
        """
        try:
            logger.info("Node[select_rules]: start")
            # Basic guards
            if state.get("validation_result", {}).get("status") != "valid":
                state["rules_result"] = {"error": "validation_not_valid"}
                logger.warning("Node[select_rules]: skipped | reason=validation_not_valid")
                return state
            if not state.get("project_id"):
                state["rules_result"] = {"error": "missing_project_id"}
                logger.warning("Node[select_rules]: skipped | reason=missing_project_id")
                return state

            # Fetch categories and master catalog
            cat_by_id: Dict[int, str] = {c.boq_category_id: c.name for c in self.db.execute(select(BOQCategory)).scalars().all()}
            masters = self.db.execute(select(MasterRuleSet).where(MasterRuleSet.is_active == 1)).scalars().all()
            logger.info("Node[select_rules]: catalog_count=%s", len(masters))
            catalog_names = [m.name for m in masters]

            # Load extracted payload for richer context
            va_id = (state.get("validation_result") or {}).get("validation_attempt_id")
            attempt_payload = None
            if va_id:
                va = self.db.query(ValidationAttempt).filter(ValidationAttempt.validation_attempt_id == va_id).first()
                attempt_payload = va.extracted_payload if va and va.extracted_payload else None

            # By default we do not skip the LLM selector. Initialize flag and wanted_names early so
            # later logic can set them without accidental overwrites.
            skip_llm = False
            wanted_names = set()

            # If the user explicitly provided a category/type in the extracted payload, prefer that
            # (generate BOQ only for that BOQ category). If no category is provided, select all master
            # rule sets by default (per current flow requirements).
            if attempt_payload and isinstance(attempt_payload, dict):
                user_cat = None
                if isinstance(attempt_payload.get("category"), str):
                    user_cat = attempt_payload.get("category").strip().lower()
                elif isinstance(attempt_payload.get("type"), str):
                    user_cat = attempt_payload.get("type").strip().lower()

                if user_cat:
                    # Try to match provided category against BOQCategory names (exact-ish match)
                    matched_cat_id = None
                    for cid, cname in cat_by_id.items():
                        n = (cname or "").strip().lower()
                        if n == user_cat or n.replace(" ", "_") == user_cat or n.replace("_", " ") == user_cat:
                            matched_cat_id = cid
                            break

                    if matched_cat_id is not None:
                        matched = [m for m in masters if m.category_id == matched_cat_id]
                        if matched:
                            wanted_names = {m.name for m in matched}
                            skip_llm = True
                            logger.info("Node[select_rules]: user requested BOQ category '%s' -> selecting %s masters", user_cat, len(wanted_names))
                    else:
                        # Unknown category value provided — fall back to selecting all master rule sets
                        wanted_names = {m.name for m in masters}
                        skip_llm = True
                        logger.info("Node[select_rules]: user provided category '%s' not matched -> selecting ALL master rule sets (%s)", user_cat, len(wanted_names))
                else:
                    # No explicit category provided: select all master rule sets by default
                    wanted_names = {m.name for m in masters}
                    skip_llm = True
                    logger.info("Node[select_rules]: no category provided -> selecting all master rule sets (%s)", len(wanted_names))

            # If the user provided only basic room geometry (rooms with dimensions) and nothing else,
            # we should generate BOQs for all master rule sets (all categories) using master defaults.
            # Validate that rooms have required fields (length, width and their units). If fields missing,
            # return a missing_fields error so API can request more info.
            if attempt_payload and isinstance(attempt_payload, dict):
                keys = set(attempt_payload.keys())
                if keys <= {"rooms"}:
                    rooms = attempt_payload.get("rooms") or []
                    if not rooms:
                        state["rules_result"] = {"error": "insufficient_details", "message": "provide more details of the building"}
                        logger.warning("Node[select_rules]: insufficient_details from payload")
                        return state
                    missing = []
                    for i, r in enumerate(rooms):
                        L = r.get("length")
                        W = r.get("width")
                        if not L or not isinstance(L, dict) or L.get("value") is None or L.get("unit") is None:
                            missing.append({"room_index": i, "field": "length"})
                        if not W or not isinstance(W, dict) or W.get("value") is None or W.get("unit") is None:
                            missing.append({"room_index": i, "field": "width"})
                    if missing:
                        state["rules_result"] = {"error": "missing_fields", "missing": missing}
                        logger.warning("Node[select_rules]: missing_fields=%s", missing)
                        return state
                    # All rooms valid: select all master rule sets
                    wanted_names = {m.name for m in masters}
                    skip_llm = True
                    logger.info("Node[select_rules]: rooms-only payload -> selecting all master rule sets (%s)", len(wanted_names))

            # If there's no extracted payload and the raw text is very short, ask for more details
            if not attempt_payload and (len((state.get("raw_input_text") or "").strip().split()) < 3):
                state["rules_result"] = {"error": "insufficient_details", "message": "provide more details of the building"}
                logger.warning("Node[select_rules]: insufficient raw input text")
                return state

            # Build LLM prompt to select from catalog
            # wanted_names already initialized above; ensure we have a set
            if not isinstance(wanted_names, set):
                wanted_names = set()
            llm_error: Optional[str] = None
            if not skip_llm and (settings.openrouter_api_key or settings.gemini_api_key):
                sys_prompt = (
                    "You are a civil estimation assistant. From the provided catalog of master rule set names, "
                    "choose which apply to the user's described scope. Return ONLY JSON: {\"selected\": [names], \"notes\": string }. "
                    "Choose only from the provided names. If insufficient info, return an empty list. Keep it concise."
                )
                user_payload = {
                    "catalog_names": catalog_names,
                    "extracted_payload": attempt_payload,
                    "raw_input_excerpt": (state.get("raw_input_text") or "")[:1000],
                }
                messages: List[Dict[str, str]] = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ]
                try:
                    if settings.openrouter_api_key:
                        content = _openrouter_chat(messages, model=settings.openrouter_model, temperature=0)
                    else:
                        content = _gemini_chat(messages, model=settings.gemini_model, temperature=0)
                    # Console log LLM output for select_rules
                    print("[LLM SELECT_RULES OUTPUT]", content)
                    data = self._extract_json_block(content)
                    sel = data.get("selected") or []
                    if isinstance(sel, list):
                        wanted_names = {str(n) for n in sel}
                except Exception as e:
                    llm_error = str(e)
                    logger.warning("Node[select_rules]: LLM selector error: %s", llm_error)

            # Deterministic fallback if LLM not configured or selection empty
            if not wanted_names:
                # safe defaults aligned with earlier heuristic
                wanted_names = {"CC-RCC-SLAB-M20", "FLR-TILE-600x600-VIT"}
                logger.info("Node[select_rules]: using fallback selection %s", list(wanted_names))

            # Validate against catalog. Use case-insensitive and substring matching to be resilient
            # to minor differences in names returned by the LLM.
            wanted_lower = {w.lower() for w in wanted_names}
            chosen = [
                m for m in masters
                if m.name.lower() in wanted_lower
                or any(w in m.name.lower() for w in wanted_lower)
                or any(m.name.lower() in w for w in wanted_lower)
            ]
            if not chosen:
                state["rules_result"] = {"error": "no_master_rules_available"}
                logger.error("Node[select_rules]: no_master_rules_available (post-validation)")
                return state

            rule_set_ids = []
            items_created = 0
            items_preview: list[dict[str, Any]] = []
            for ms in chosen:
                # Create a RuleSet for each selected master rule set
                rs = RuleSet(user_id=state["user_id"], project_id=state["project_id"], name=ms.name)
                self.db.add(rs)
                self.db.flush()
                rule_set_ids.append(rs.rule_set_id)
                logger.info("Node[select_rules]: created rule_set_id=%s name=%s", rs.rule_set_id, ms.name)
                m_items = self.db.execute(select(MasterRuleItem).where(MasterRuleItem.master_rule_set_id == ms.master_rule_set_id)).scalars().all()
                for mi in m_items:
                    # Ensure we preserve master defaults (value, unit, formula) when cloning
                    unit_only, basis = self._parse_unit_basis(mi.unit)
                    ri = RuleItem(
                        rule_set_id=rs.rule_set_id,
                        category_id=ms.category_id,
                        key=mi.key,
                        unit=mi.unit or "",
                        rate_basis=basis,
                        description=mi.description,
                        value=mi.default_value if getattr(mi, "default_value", None) is not None else None,
                        resolved_rate=mi.default_value if getattr(mi, "default_value", None) is not None else None,
                        formula=mi.formula if getattr(mi, "formula", None) is not None else None,
                    )
                    self.db.add(ri)
                    items_created += 1
                    if state.get("preview"):
                        items_preview.append({
                            "category": cat_by_id.get(ms.category_id),
                            "key": mi.key,
                            "unit": mi.unit,
                            "description": mi.description,
                        })

            self.db.commit()
            logger.info("Node[select_rules]: done | items_created=%s", items_created)
            # For downstream nodes, you may need to process each rule_set_id separately
            state["rules_result"] = {
                "rule_set_ids": rule_set_ids,
                "items_created": items_created,
                "items": items_preview if state.get("preview") else None,
                "llm_notes": None if not llm_error else f"selector_error: {llm_error}",
                "selected_set_names": [m.name for m in chosen],
            }
            return state
        except Exception as e:
            state["rules_result"] = {"error": str(e)}
            logger.exception("Node[select_rules]: error")
            return state

    async def compute_boq_node(self, state: ValidationFlowState) -> ValidationFlowState:
        try:
            logger.info("Node[compute_boq]: start")
            rs_ids = (state.get("rules_result") or {}).get("rule_set_ids") or []
            va_id = (state.get("validation_result") or {}).get("validation_attempt_id")
            if not rs_ids or not va_id:
                state["compute_result"] = {"skipped": True, "reason": "missing_rule_set_or_validation"}
                logger.warning("Node[compute_boq]: skipped | reason=missing_rule_set_or_validation")
                return state
            if not state.get("project_id"):
                state["compute_result"] = {"skipped": True, "reason": "missing_project_id"}
                logger.warning("Node[compute_boq]: skipped | reason=missing_project_id")
                return state

            boqs = []
            total_items = 0
            for rs_id in rs_ids:
                try:
                    boq_id, count = compute_boq(
                        self.db,
                        user_id=state["user_id"],
                        project_id=state["project_id"],
                        validation_attempt_id=va_id,
                        rule_set_id=rs_id,
                    )
                    # Gather BOQ items to include in compute JSON
                    items = self.db.execute(select(BOQItem).where(BOQItem.boq_id == boq_id)).scalars().all()
                    items_payload = []
                    for it in items:
                        items_payload.append({
                            "boq_item_id": it.boq_item_id if getattr(it, "boq_item_id", None) is not None else None,
                            "material_name": it.material_name,
                            "rule_item_id": it.rule_item_id,
                            "category_id": it.category_id,
                            "quantity": str(it.quantity) if it.quantity is not None else None,
                            "unit": it.unit,
                        })

                    compute_payload = {
                        "rule_set_id": rs_id,
                        "boq_id": boq_id,
                        "items_created": count,
                        "items": items_payload,
                    }

                    # Store the LLM rule-selection JSON into BOQ.compute_json (the rules_result
                    # coming from the select_rules node), not the whole compute payload.
                    boq_obj = self.db.get(BOQ, boq_id)
                    if boq_obj:
                        try:
                            # Start from the rules_result produced earlier
                            rules_json = state.get("rules_result") or {}

                            # Also assemble a compact raw payload for this rule_set (key, unit, value)
                            rs_obj = self.db.get(RuleSet, rs_id)
                            ri_objs = self.db.execute(select(RuleItem).where(RuleItem.rule_set_id == rs_id)).scalars().all()
                            items_for_raw: list[dict[str, Any]] = []
                            for ri in ri_objs:
                                items_for_raw.append({
                                    "key": getattr(ri, "key", None),
                                    "unit": getattr(ri, "unit", None),
                                    "value": getattr(ri, "value", None) if getattr(ri, "value", None) is not None else getattr(ri, "resolved_rate", None),
                                })
                            rs_name = getattr(rs_obj, "name", str(rs_id)) if rs_obj is not None else str(rs_id)
                            raw_payload = {rs_name: {"rule_set_id": rs_id, "items": items_for_raw}}

                            # Combine rules_result with the raw payload into compute_json so a single
                            # column contains both LLM selection and the per-rule-set raw items.
                            combined = {"rules_result": rules_json, "raw": raw_payload}
                            try:
                                combined_str = json.dumps(combined, ensure_ascii=False)
                            except Exception:
                                combined_str = str(combined)
                            logger.info("Node[compute_boq]: writing compute_json for boq_id=%s (len=%s) snippet=%s", boq_id, len(combined_str), combined_str[:200])
                            boq_obj.compute_json = combined_str
                            self.db.add(boq_obj)
                            try:
                                self.db.commit()
                                logger.info("Node[compute_boq]: successfully wrote compute_json for boq_id=%s", boq_id)
                            except Exception:
                                try:
                                    self.db.rollback()
                                except Exception:
                                    pass
                                logger.exception("Node[compute_boq]: failed to commit compute_json for boq_id=%s", boq_id)
                        except Exception:
                            self.db.rollback()

                    # Upsert BOQ items into `benchmark_materials` by (project_id, name).
                    # Store quantity, unit and a notes JSON with source ids for traceability.
                    materials_payload = []
                    for it in items:
                        try:
                            name = it.material_name or ""
                            existing = self.db.query(BenchmarkMaterial).filter(
                                BenchmarkMaterial.project_id == state["project_id"],
                                BenchmarkMaterial.name == name,
                            ).first()
                            notes_obj = {
                                "source": "boq_item",
                                "boq_id": boq_id,
                                "boq_item_id": getattr(it, "boq_item_id", None),
                                "rule_item_id": getattr(it, "rule_item_id", None),
                            }
                            if existing:
                                # update existing record quantity/unit/notes
                                existing.quantity = it.quantity
                                existing.unit = it.unit
                                # append trace info to notes
                                try:
                                    prev = existing.notes or ""
                                    existing.notes = prev + "\n" + json.dumps(notes_obj, ensure_ascii=False)
                                except Exception:
                                    existing.notes = json.dumps(notes_obj, ensure_ascii=False)
                                self.db.add(existing)
                                self.db.commit()
                                bm_id = existing.benchmark_material_id
                            else:
                                bm = BenchmarkMaterial(
                                    user_id=state["user_id"],
                                    project_id=state["project_id"],
                                    category_id=None,
                                    name=name,
                                    quantity=it.quantity,
                                    unit=it.unit,
                                    default_wastage_multiplier=1.0,
                                    notes=json.dumps(notes_obj, ensure_ascii=False),
                                )
                                self.db.add(bm)
                                self.db.commit()
                                bm_id = bm.benchmark_material_id

                            materials_payload.append({
                                "benchmark_material_id": bm_id,
                                "name": name,
                                "quantity": str(it.quantity) if it.quantity is not None else None,
                                "unit": it.unit,
                                "boq_item_id": getattr(it, "boq_item_id", None),
                            })
                        except Exception:
                            try:
                                self.db.rollback()
                            except Exception:
                                pass
                            logger.exception("Node[compute_boq]: failed to upsert benchmark_material for boq_item=%s", getattr(it, "boq_item_id", None))

                    # Attach benchmark_materials info to compute_payload for API response
                    compute_payload["benchmark_materials"] = materials_payload

                    boqs.append({"rule_set_id": rs_id, "boq_id": boq_id, "items_created": count, "compute": compute_payload})
                    total_items += count
                    logger.info("Node[compute_boq]: created boq_id=%s for rule_set_id=%s items=%s", boq_id, rs_id, count)
                except Exception as e:
                    logger.exception("Node[compute_boq]: failed for rule_set_id=%s", rs_id)
                    boqs.append({"rule_set_id": rs_id, "error": str(e)})

            state["compute_result"] = {"boqs": boqs, "items_created_total": total_items}
            logger.info("Node[compute_boq]: done | boqs_count=%s items_total=%s", len(boqs), total_items)
            return state
        except Exception as e:
            state["compute_result"] = {"error": str(e)}
            logger.exception("Node[compute_boq]: error")
            return state

    async def assemble_raw_node(self, state: ValidationFlowState) -> ValidationFlowState:
        """Assemble a compact raw JSON per BOQ containing RuleSet name -> list of RuleItems

        Stored shape (example):
        {
          "CC-RCC-SLAB-M20": {
              "rule_set_id": 71,
              "items": [{"key": "cement_bags", "unit": "bags_per_m3", "value": 7.992}, ...]
          },
          "FLR-TILE-600x600-VIT": { ... }
        }

        This will be persisted to `BOQ.raw_json` for each BOQ created by `compute_boq_node`.
        """
        try:
            logger.info("Node[assemble_raw]: start")
            boqs = (state.get("compute_result") or {}).get("boqs") or []
            if not boqs:
                logger.info("Node[assemble_raw]: no boqs to process")
                return state

            for b in boqs:
                try:
                    rs_id = b.get("rule_set_id")
                    boq_id = b.get("boq_id")
                    if rs_id is None or boq_id is None:
                        logger.warning("Node[assemble_raw]: missing rs_id or boq_id in boqs entry: %s", b)
                        continue

                    # Fetch rule set and items
                    rs_obj = self.db.get(RuleSet, rs_id)
                    ri_objs = self.db.execute(select(RuleItem).where(RuleItem.rule_set_id == rs_id)).scalars().all()

                    items: List[Dict[str, Any]] = []
                    for ri in ri_objs:
                        items.append({
                            "key": getattr(ri, "key", None),
                            "unit": getattr(ri, "unit", None),
                            "value": getattr(ri, "value", None) if getattr(ri, "value", None) is not None else getattr(ri, "resolved_rate", None),
                        })

                    rs_name = getattr(rs_obj, "name", str(rs_id)) if rs_obj is not None else str(rs_id)
                    raw_payload = {rs_name: {"rule_set_id": rs_id, "items": items}}

                    # Persist onto BOQ.raw_json if the model has that attribute
                    boq_obj = self.db.get(BOQ, boq_id)
                    if not boq_obj:
                        logger.warning("Node[assemble_raw]: BOQ not found boq_id=%s", boq_id)
                        continue

                    # Merge the assembled raw payload into BOQ.compute_json (single canonical field)
                    try:
                        existing = {}
                        if getattr(boq_obj, "compute_json", None):
                            try:
                                existing = json.loads(boq_obj.compute_json)
                            except Exception:
                                existing = {}

                        # Merge raw payload into existing['raw'] while preserving any existing keys
                        raw_section = existing.get("raw", {}) if isinstance(existing, dict) else {}
                        # raw_payload is keyed by rule set name; update/overwrite those keys
                        raw_section.update(raw_payload)
                        if isinstance(existing, dict):
                            existing["raw"] = raw_section
                        else:
                            existing = {"raw": raw_section}

                        try:
                            existing_str = json.dumps(existing, ensure_ascii=False)
                        except Exception:
                            existing_str = str(existing)
                        logger.info("Node[assemble_raw]: writing merged compute_json for boq_id=%s (len=%s) snippet=%s", boq_id, len(existing_str), existing_str[:200])
                        boq_obj.compute_json = existing_str
                        self.db.add(boq_obj)
                        try:
                            self.db.commit()
                            logger.info("Node[assemble_raw]: merged raw into compute_json for boq_id=%s rule_set_id=%s", boq_id, rs_id)
                        except Exception:
                            try:
                                self.db.rollback()
                            except Exception:
                                pass
                            logger.exception("Node[assemble_raw]: failed to commit merged compute_json for boq_id=%s", boq_id)
                    except Exception:
                        try:
                            self.db.rollback()
                        except Exception:
                            pass
                        logger.exception("Node[assemble_raw]: failed to merge raw into compute_json for boq_id=%s", boq_id)

                except Exception:
                    logger.exception("Node[assemble_raw]: failed processing boqs entry=%s", b)

            logger.info("Node[assemble_raw]: done")
            return state
        except Exception as e:
            logger.exception("Node[assemble_raw]: error")
            return state
