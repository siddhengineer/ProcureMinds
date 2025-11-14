"""
Quotation extraction schemas for vendor email processing.

This module defines Pydantic models for quotation extraction
and benchmark matching following PEP8 standards.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class AttachmentData(BaseModel):
    """Schema for email attachment information."""

    filename: str = Field(..., description="Name of the attachment file")
    file_type: str = Field(
        ..., description="File type (excel, pdf, etc.)"
    )
    file_path: Optional[str] = Field(
        default=None, description="Path to the attachment file"
    )
    content: Optional[bytes] = Field(
        default=None, description="Binary content of the file"
    )


class BenchmarkItem(BaseModel):
    """Schema for benchmark product information from database."""

    id: int = Field(..., description="Benchmark ID")
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    quality_standard: Optional[str] = Field(
        default=None, description="Quality standard specification"
    )
    unit: str = Field(..., description="Unit of measurement")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class QuotedItem(BaseModel):
    """Schema for individual quoted item from vendor."""

    item_name: str = Field(..., description="Name of the quoted item")
    description: Optional[str] = Field(
        default=None, description="Item description from vendor"
    )
    quantity: Optional[float] = Field(
        default=None, description="Quoted quantity"
    )
    unit: str = Field(..., description="Unit of measurement")
    unit_price: Optional[Decimal] = Field(
        default=None, description="Price per unit"
    )
    total_price: Optional[Decimal] = Field(
        default=None, description="Total price for quantity"
    )
    delivery_time: Optional[str] = Field(
        default=None, description="Delivery timeline"
    )
    specifications: Optional[dict[str, Any]] = Field(
        default=None, description="Technical specifications"
    )
    matched_benchmark_id: Optional[int] = Field(
        default=None, description="ID of matched benchmark item"
    )
    match_confidence: Optional[str] = Field(
        default=None, description="Confidence of benchmark match"
    )


class QuotationSummary(BaseModel):
    """Schema for extracted quotation summary."""

    vendor_name: Optional[str] = Field(
        default=None, description="Vendor/sender name"
    )
    email_subject: str = Field(..., description="Email subject line")
    email_date: Optional[datetime] = Field(
        default=None, description="Email received date"
    )
    summary: str = Field(
        ..., description="Natural language summary of the quotation"
    )
    quoted_items: list[QuotedItem] = Field(
        default_factory=list, description="List of quoted items"
    )
    total_items_count: int = Field(
        ..., description="Total number of items quoted"
    )
    matched_benchmarks_count: int = Field(
        ..., description="Number of items matched to benchmarks"
    )
    currency: str = Field(default="INR", description="Currency code")
    payment_terms: Optional[str] = Field(
        default=None, description="Payment terms mentioned"
    )
    validity_period: Optional[str] = Field(
        default=None, description="Quotation validity period"
    )
    additional_notes: Optional[str] = Field(
        default=None, description="Additional notes or conditions"
    )
    extraction_confidence: str = Field(
        ..., description="Overall extraction confidence: high, medium, low"
    )
    extraction_method: str = Field(
        ..., description="Method used: openai, attachment, hybrid"
    )


class QuotationExtractionInput(BaseModel):
    """Input schema for quotation extraction."""

    email_content: str = Field(..., description="Email body content")
    subject: str = Field(default="", description="Email subject")
    sender: Optional[str] = Field(
        default=None, description="Sender email address"
    )
    attachments: list[AttachmentData] = Field(
        default_factory=list, description="Email attachments"
    )
    benchmarks: list[BenchmarkItem] = Field(
        default_factory=list, description="Available benchmark items"
    )


class QuotationNodeState(BaseModel):
    """State schema for quotation extraction node in LangGraph."""

    email_content: str
    subject: str = ""
    sender: Optional[str] = None
    attachments: list[AttachmentData] = Field(default_factory=list)
    benchmarks: list[BenchmarkItem] = Field(default_factory=list)
    quotation_summary: Optional[QuotationSummary] = None
    error: Optional[str] = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
