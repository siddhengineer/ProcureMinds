"""
Email Processing Workflow with Intent Classification.

This module demonstrates LangGraph workflow integration with
intent classification node following PEP8 standards.
"""

from typing import Any

from langgraph.graph import END, StateGraph

from app.workflows.intent_node import (
    EmailWorkflowState,
    IntentClassificationNode,
)


class EmailProcessingWorkflow:
    """LangGraph workflow for email processing with intent routing."""

    def __init__(self) -> None:
        """Initialize the email processing workflow."""
        self.intent_node = IntentClassificationNode()
        self.graph = self._build_graph()

    async def quotation_processing_node(
        self, state: EmailWorkflowState
    ) -> EmailWorkflowState:
        """
        Process quotation-related emails.

        This node handles emails classified as QUOTATION intent.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with quotation processing results
        """
        # TODO: Implement quotation processing logic
        state["quotation_data"] = {
            "status": "processed",
            "message": "Quotation request identified and queued",
        }
        return state

    async def query_processing_node(
        self, state: EmailWorkflowState
    ) -> EmailWorkflowState:
        """
        Process quotation query emails (reserved for future use).

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        # Reserved for future implementation
        state["quotation_data"] = {
            "status": "queued",
            "message": "Query processing not yet implemented",
        }
        return state

    async def final_node(
        self, state: EmailWorkflowState
    ) -> EmailWorkflowState:
        """
        Aggregate final results.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with final output
        """
        state["final_output"] = {
            "intent": state.get("intent"),
            "confidence": state.get("intent_confidence"),
            "processed": state.get("should_process"),
            "quotation_data": state.get("quotation_data"),
            "error": state.get("error"),
        }
        return state

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow with intent-based routing.

        Returns:
            Compiled StateGraph ready for execution
        """
        workflow = StateGraph(EmailWorkflowState)

        # Add nodes
        workflow.add_node(
            "intent_classification", self.intent_node.classify_intent
        )
        workflow.add_node(
            "quotation_processing", self.quotation_processing_node
        )
        workflow.add_node("query_processing", self.query_processing_node)
        workflow.add_node("final_node", self.final_node)

        # Set entry point
        workflow.set_entry_point("intent_classification")

        # Add conditional routing based on intent
        workflow.add_conditional_edges(
            "intent_classification",
            self.intent_node.route_based_on_intent,
            {
                "quotation_processing": "quotation_processing",
                "query_processing": "query_processing",
                "end": "final_node",
            },
        )

        # Connect processing nodes to final node
        workflow.add_edge("quotation_processing", "final_node")
        workflow.add_edge("query_processing", "final_node")
        workflow.add_edge("final_node", END)

        return workflow.compile()

    async def execute(
        self,
        email_content: str,
        subject: str = "",
        sender: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute the email processing workflow.

        Args:
            email_content: The body of the email
            subject: Email subject line (optional)
            sender: Email sender address (optional)

        Returns:
            Final workflow output with classification and processing results
        """
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

        result = await self.graph.ainvoke(initial_state)
        return result.get("final_output", {})
