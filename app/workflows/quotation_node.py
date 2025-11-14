"""Quotation Extraction Node for LangGraph Workflow."""

from typing import Any

from app.schemas.quotation import QuotationSummary
from app.services.email_extraction import QuotationExtractor


class QuotationExtractionNode:
    """LangGraph node for quotation extraction from vendor emails."""

    def __init__(self) -> None:
        """Initialize the quotation extraction node."""
        self.extractor = QuotationExtractor()

    async def extract_quotation(
        self, state: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract quotation data and update workflow state."""
        try:
            email_content = state.get("email_content", "")
            subject = state.get("subject", "")
            sender = state.get("sender")
            attachments = state.get("attachments", [])
            benchmarks = state.get("benchmarks", [])

            summary: QuotationSummary = self.extractor.extract(
                email_content=email_content,
                subject=subject,
                sender=sender,
                attachments=attachments,
                benchmarks=benchmarks,
            )

            state["quotation_summary"] = summary.model_dump()
            state["extraction_complete"] = True
            state["error"] = None

            return state

        except Exception as e:
            state["quotation_summary"] = None
            state["extraction_complete"] = False
            state["error"] = f"Quotation extraction error: {str(e)}"

            return state
