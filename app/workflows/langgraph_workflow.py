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
        result = run_validation(
            self.db,
            user_id=state["user_id"],
            project_id=state.get("project_id"),
            raw_input_text=state["raw_input_text"],
        )
        state["validation_result"] = result
        logger.info(
            "Node[validate]: done | status=%s attempt_id=%s",
            result.get("status"), result.get("validation_attempt_id")
        )
        return state

    def _build_graph(self) -> StateGraph:
        """Build the validation + ruleset generation workflow."""
        workflow = StateGraph(ValidationFlowState)

        workflow.add_node("input", self.input_node)
        workflow.add_node("validate", self.validation_node)
        workflow.add_node("select_rules", self.select_rules_from_master_node)
        workflow.add_node("compute_boq", self.compute_boq_node)
        workflow.add_node("generate_csv", self.generate_csv_node)

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
        workflow.add_edge("compute_boq", "generate_csv")
        workflow.add_edge("generate_csv", END)

        return workflow.compile()
    async def generate_csv_node(self, state: ValidationFlowState) -> ValidationFlowState:
        import csv
        from io import StringIO
        logger.info("Node[generate_csv]: start")
        boq_id = (state.get("compute_result") or {}).get("boq_id")
        if not boq_id:
            state["csv_result"] = {"skipped": True, "reason": "missing_boq_id"}
            logger.warning("Node[generate_csv]: skipped | reason=missing_boq_id")
            return state
        # Fetch BOQ and items
        boq = self.db.get(BOQ, boq_id)
        if not boq:
            state["csv_result"] = {"error": "boq_not_found"}
            logger.error("Node[generate_csv]: boq_not_found")
            return state
        items = self.db.execute(select(BOQItem).where(BOQItem.boq_id == boq_id)).scalars().all()
        categories = {c.boq_category_id: c.name for c in self.db.execute(select(BOQCategory)).scalars().all()}
        rule_sets = {r.rule_set_id: r for r in self.db.execute(select(RuleSet)).scalars().all()}
        rule_items = {ri.rule_item_id: ri for ri in self.db.execute(select(RuleItem)).scalars().all()}

        # Prepare CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Category",
            "Rule Set",
            "Material Name",
            "Rule Item Key",
            "Proportion/Formula",
            "Unit",
            "Quantity",
        ])
        for item in items:
            category = categories.get(item.category_id, "Unknown")
            rule_item = rule_items.get(item.rule_item_id)
            rule_set = rule_sets.get(boq.rule_set_id)
            writer.writerow([
                category,
                rule_set.name if rule_set else "",
                item.material_name,
                rule_item.key if rule_item else "",
                rule_item.formula if rule_item and rule_item.formula else (str(rule_item.value) if rule_item and rule_item.value is not None else ""),
                item.unit,
                str(item.quantity),
            ])
        csv_data = output.getvalue()
        output.close()
        # Save to file (or attach to state)
        csv_path = f"boq_{boq_id}.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(csv_data)
        state["csv_result"] = {"csv_path": csv_path, "row_count": len(items)}
        logger.info(f"Node[generate_csv]: done | csv_path={csv_path} row_count={len(items)}")
        return state

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
            "Execute[full]: done | v_status=%s rs_id=%s boq=%s",
            (result.get("validation_result") or {}).get("status"),
            (result.get("rules_result") or {}).get("rule_set_id"),
            (result.get("compute_result") or {}).get("boq_id"),
        )
        return {
            "validation_result": result["validation_result"],
            "rules_result": result["rules_result"],
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
            "Execute[generic]: done | v_status=%s rs_id=%s boq=%s",
            (result.get("validation_result") or {}).get("status"),
            (result.get("rules_result") or {}).get("rule_set_id"),
            (result.get("compute_result") or {}).get("boq_id"),
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

            # Build LLM prompt to select from catalog
            wanted_names: set[str] = set()
            llm_error: Optional[str] = None
            if settings.openrouter_api_key or settings.gemini_api_key:
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

            # Validate against catalog
            chosen = [m for m in masters if m.name in wanted_names]
            if not chosen:
                state["rules_result"] = {"error": "no_master_rules_available"}
                logger.error("Node[select_rules]: no_master_rules_available (post-validation)")
                return state

            # Create RuleSet
            rs = RuleSet(user_id=state["user_id"], project_id=state["project_id"], name=(state.get("default")))
            self.db.add(rs)
            self.db.flush()
            logger.info("Node[select_rules]: created rule_set_id=%s names=%s", rs.rule_set_id, [m.name for m in chosen])

            items_created = 0
            items_preview: list[dict[str, Any]] = []
            for ms in chosen:
                m_items = self.db.execute(select(MasterRuleItem).where(MasterRuleItem.master_rule_set_id == ms.master_rule_set_id)).scalars().all()
                for mi in m_items:
                    unit_only, basis = self._parse_unit_basis(mi.unit)
                    ri = RuleItem(
                        rule_set_id=rs.rule_set_id,
                        category_id=ms.category_id,
                        key=mi.key,
                        unit=mi.unit,
                        rate_basis=basis,
                        description=mi.description,
                        value=None,
                        resolved_rate=None,
                        formula=None,
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
            state["rules_result"] = {
                "rule_set_id": rs.rule_set_id,
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
            rs_id = (state.get("rules_result") or {}).get("rule_set_id")
            va_id = (state.get("validation_result") or {}).get("validation_attempt_id")
            if not rs_id or not va_id:
                state["compute_result"] = {"skipped": True, "reason": "missing_rule_set_or_validation"}
                logger.warning("Node[compute_boq]: skipped | reason=missing_rule_set_or_validation")
                return state
            if not state.get("project_id"):
                state["compute_result"] = {"skipped": True, "reason": "missing_project_id"}
                logger.warning("Node[compute_boq]: skipped | reason=missing_project_id")
                return state
            boq_id, count = compute_boq(
                self.db,
                user_id=state["user_id"],
                project_id=state["project_id"],
                validation_attempt_id=va_id,
                rule_set_id=rs_id,
            )
            state["compute_result"] = {"boq_id": boq_id, "items_created": count}
            logger.info("Node[compute_boq]: done | boq_id=%s items_created=%s", boq_id, count)
            return state
        except Exception as e:
            state["compute_result"] = {"error": str(e)}
            logger.exception("Node[compute_boq]: error")
            return state
