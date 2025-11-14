"""
Intent classification schemas for email processing.

This module defines Pydantic models for intent classification
following PEP8 standards.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EmailIntent(str, Enum):
    """Email intent categories for classification."""

    QUOTATION = "quotation"
    QUOTATION_QUERIES = "quotation_queries"
    CASUAL = "casual"


class EmailInput(BaseModel):
    """Input schema for email intent classification."""

    email_content: str = Field(
        ...,
        description="The body content of the email",
        min_length=1
    )
    subject: str = Field(
        default="",
        description="Email subject line (optional)"
    )
    sender: Optional[str] = Field(
        default=None,
        description="Email sender address (optional)"
    )


class IntentClassificationResult(BaseModel):
    """Result schema for intent classification."""

    intent: EmailIntent = Field(
        ...,
        description="Classified intent category"
    )
    confidence: str = Field(
        ...,
        description="Confidence level: high, medium, or low"
    )
    method: str = Field(
        ...,
        description="Classification method used: openai, keyword, or fallback"
    )
    should_process: bool = Field(
        ...,
        description="Whether email should proceed to next node"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Optional reasoning for classification"
    )

    class Config:
        """Pydantic config."""

        use_enum_values = True


class IntentNodeState(BaseModel):
    """State schema for intent classification node in LangGraph."""

    email_content: str
    subject: str = ""
    sender: Optional[str] = None
    intent_result: Optional[IntentClassificationResult] = None
    error: Optional[str] = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
