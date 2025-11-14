"""
Intent Classification Node for LangGraph Workflow.

This module provides a LangGraph-compatible node for email intent
classification following PEP8 standards.
"""

from typing import Any, TypedDict

from app.schemas.intent import (
    EmailIntent,
    IntentClassificationResult,
    IntentNodeState,
)
from app.services.intent import IntentClassifier


class EmailWorkflowState(TypedDict):
    """State schema for email processing workflow."""

    # Input fields
    email_content: str
    subject: str
    sender: str | None

    # Intent classification results
    intent: str | None
    intent_confidence: str | None
    intent_method: str | None
    should_process: bool

    # Downstream processing
    quotation_data: dict[str, Any] | None
    final_output: dict[str, Any] | None
    error: str | None


class IntentClassificationNode:
    """LangGraph node for email intent classification."""

    def __init__(self) -> None:
        """Initialize the intent classification node."""
        self.classifier = IntentClassifier()

    async def classify_intent(
        self, state: EmailWorkflowState
    ) -> EmailWorkflowState:
        """
        Classify email intent and update workflow state.

        This is the main node function for LangGraph integration.

        Args:
            state: Current workflow state containing email data

        Returns:
            Updated workflow state with classification results
        """
        try:
            # Extract email data from state
            email_content = state.get("email_content", "")
            subject = state.get("subject", "")

            # Perform classification
            result: IntentClassificationResult = self.classifier.classify(
                email_content=email_content,
                subject=subject,
                use_fallback=True,
            )

            # Update state with results
            state["intent"] = result.intent.value
            state["intent_confidence"] = result.confidence
            state["intent_method"] = result.method
            state["should_process"] = result.should_process
            state["error"] = None

            return state

        except Exception as e:
            # Handle errors gracefully
            state["intent"] = EmailIntent.CASUAL.value
            state["intent_confidence"] = "low"
            state["intent_method"] = "error"
            state["should_process"] = False
            state["error"] = f"Intent classification error: {str(e)}"

            return state

    def route_based_on_intent(
        self, state: EmailWorkflowState
    ) -> str:
        """
        Router function to determine next node based on intent.

        This function is used with LangGraph's conditional edges
        to route emails to appropriate processing nodes.

        Args:
            state: Current workflow state

        Returns:
            Name of the next node to execute
        """
        should_process = state.get("should_process", False)
        intent = state.get("intent", "casual")

        if should_process and intent == EmailIntent.QUOTATION.value:
            return "quotation_processing"
        elif intent == EmailIntent.QUOTATION_QUERIES.value:
            # Reserved for future use
            return "query_processing"
        else:
            # Casual emails are ignored
            return "end"


# Convenience function for standalone usage
async def classify_email_node(
    state: EmailWorkflowState,
) -> EmailWorkflowState:
    """
    Standalone async function for intent classification.

    Args:
        state: Email workflow state

    Returns:
        Updated workflow state
    """
    node = IntentClassificationNode()
    return await node.classify_intent(state)
