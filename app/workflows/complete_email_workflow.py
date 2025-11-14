"""Complete Email Processing Workflow with Intent and Quotation Extraction."""

from typing import Any

from langgraph.graph import END, StateGraph

from app.workflows.intent_node import (
    EmailWorkflowState,
    IntentClassificationNode,
)
from app.workflows.quotation_node import QuotationExtractionNode


class CompleteEmailWorkflow:
    """Complete LangGraph workflow for email processing."""

    def __init__(self) -> None:
        """Initialize the complete email processing workflow."""
        self.intent_node = IntentClassificationNode()
        self.quotation_node = QuotationExtractionNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the complete LangGraph workflow."""
        workflow = StateGraph(EmailWorkflowState)

        # Add nodes
        workflow.add_node(
            "intent_classification", self.intent_node.classify_intent
        )
        workflow.add_node(
            "quotation_extraction", self.quotation_node.extract_quotation
        )

        # Set entry point
        workflow.set_entry_point("intent_classification")

        # Add conditional routing based on intent
        workflow.add_conditional_edges(
            "intent_classification",
            self.intent_node.route_based_on_intent,
            {
                "quotation_processing": "quotation_extraction",
                "query_processing": END,
                "end": END,
            },
        )

        # Connect quotation extraction to end
        workflow.add_edge("quotation_extraction", END)

        return workflow.compile()

    async def execute(
        self,
        email_content: str,
        subject: str = "",
        sender: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        benchmarks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute the complete email processing workflow."""
        initial_state: EmailWorkflowState = {
            "email_content": email_content,
            "subject": subject,
            "sender": sender,
            "intent": None,
            "intent_confidence": None,
            "intent_method": None,
            "should_process": False,
            "quotation_data": None,
            "final_output": None,
            "error": None,
        }

        # Add optional fields
        if attachments:
            initial_state["attachments"] = attachments
        if benchmarks:
            initial_state["benchmarks"] = benchmarks

        result = await self.graph.ainvoke(initial_state)
        return result
