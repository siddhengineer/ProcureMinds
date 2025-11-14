"""
Email Quotation Extraction Service.

Extracts quotation data from vendor emails including attachments
(Excel/PDF) and matches against benchmark items.

This module follows PEP8 standards and integrates with OpenAI.
"""

import io
import json
import os
import re
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from app.schemas.quotation import (
    AttachmentData,
    BenchmarkItem,
    QuotationSummary,
    QuotedItem,
)

load_dotenv()


class QuotationExtractor:
    """Extracts quotation data from vendor emails and attachments."""

    def __init__(self) -> None:
        """Initialize the quotation extractor with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables"
            )

        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def _extract_from_excel(
        self, attachment: AttachmentData
    ) -> Optional[str]:
        """
        Extract data from Excel attachment.

        Args:
            attachment: Excel attachment data

        Returns:
            Extracted text representation of Excel data
        """
        try:
            if attachment.content:
                df = pd.read_excel(io.BytesIO(attachment.content))
            elif attachment.file_path:
                df = pd.read_excel(attachment.file_path)
            else:
                return None

            # Convert DataFrame to readable text format
            text_data = f"Excel File: {attachment.filename}\n\n"
            text_data += df.to_string(index=False)

            return text_data

        except Exception as e:
            print(f"Excel extraction error: {e}")
            return None

    def _extract_from_pdf(
        self, attachment: AttachmentData
    ) -> Optional[str]:
        """
        Extract data from PDF attachment.

        Args:
            attachment: PDF attachment data

        Returns:
            Extracted text from PDF
        """
        try:
            # Try using PyPDF2 for text extraction
            import PyPDF2

            if attachment.content:
                pdf_file = io.BytesIO(attachment.content)
            elif attachment.file_path:
                pdf_file = open(attachment.file_path, "rb")
            else:
                return None

            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_data = f"PDF File: {attachment.filename}\n\n"

            for page_num, page in enumerate(pdf_reader.pages, 1):
                text_data += f"--- Page {page_num} ---\n"
                text_data += page.extract_text()
                text_data += "\n\n"

            if hasattr(pdf_file, "close"):
                pdf_file.close()

            return text_data

        except ImportError:
            print("PyPDF2 not installed. Install with: pip install PyPDF2")
            return None
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return None

    def _extract_attachment_data(
        self, attachments: list[AttachmentData]
    ) -> str:
        """
        Extract data from all attachments.

        Args:
            attachments: List of email attachments

        Returns:
            Combined extracted text from all attachments
        """
        extracted_data = ""

        for attachment in attachments:
            file_type = attachment.file_type.lower()

            if "excel" in file_type or file_type in ["xlsx", "xls"]:
                data = self._extract_from_excel(attachment)
                if data:
                    extracted_data += data + "\n\n"

            elif "pdf" in file_type:
                data = self._extract_from_pdf(attachment)
                if data:
                    extracted_data += data + "\n\n"

        return extracted_data

    def _build_benchmark_context(
        self, benchmarks: list[BenchmarkItem]
    ) -> str:
        """
        Build context string from benchmark items.

        Args:
            benchmarks: List of benchmark items from database

        Returns:
            Formatted benchmark context for prompt
        """
        if not benchmarks:
            return "No benchmarks available."

        context = "Available Benchmark Items:\n\n"
        for idx, benchmark in enumerate(benchmarks, 1):
            context += f"{idx}. {benchmark.name}\n"
            context += f"   - ID: {benchmark.id}\n"
            context += f"   - Category: {benchmark.category}\n"
            context += f"   - Unit: {benchmark.unit}\n"
            if benchmark.quality_standard:
                context += (
                    f"   - Quality: {benchmark.quality_standard}\n"
                )
            if benchmark.notes:
                context += f"   - Notes: {benchmark.notes}\n"
            context += "\n"

        return context

    def _extract_with_openai(
        self,
        email_content: str,
        subject: str,
        attachment_data: str,
        benchmarks: list[BenchmarkItem],
    ) -> QuotationSummary:
        """
        Extract quotation data using OpenAI.

        Args:
            email_content: Email body content
            subject: Email subject line
            attachment_data: Extracted attachment text
            benchmarks: Available benchmark items

        Returns:
            QuotationSummary with extracted data
        """
        benchmark_context = self._build_benchmark_context(benchmarks)

        prompt = f"""You are an expert at extracting quotation data from vendor emails.
Analyze the following email and any attachments to extract quotation information.

Email Subject: {subject}

Email Content:
{email_content}

{f"Attachment Data:\n{attachment_data}" if attachment_data else "No attachments."}

{benchmark_context}

Extract the following information and return as JSON:
1. Vendor name (if mentioned)
2. A brief summary of what the vendor is offering
3. List of quoted items with:
   - item_name: Name of the product
   - description: Product description
   - quantity: Quantity quoted (if mentioned)
   - unit: Unit of measurement (bags, m3, kg, etc.)
   - unit_price: Price per unit (extract number only)
   - total_price: Total price (if mentioned)
   - delivery_time: Delivery timeline (if mentioned)
   - specifications: Any technical specs as a dict
   - matched_benchmark_id: ID of matching benchmark (if applicable)
   - match_confidence: "high", "medium", or "low" for benchmark match

4. Total number of items quoted
5. Number of items that match available benchmarks
6. Currency (default INR)
7. Payment terms (if mentioned)
8. Validity period (if mentioned)
9. Additional notes or conditions

Return ONLY valid JSON in this exact format:
{{
  "vendor_name": "string or null",
  "summary": "Brief summary of the quotation",
  "quoted_items": [
    {{
      "item_name": "string",
      "description": "string or null",
      "quantity": number or null,
      "unit": "string",
      "unit_price": "string or null",
      "total_price": "string or null",
      "delivery_time": "string or null",
      "specifications": {{}},
      "matched_benchmark_id": number or null,
      "match_confidence": "string or null"
    }}
  ],
  "total_items_count": number,
  "matched_benchmarks_count": number,
  "currency": "string",
  "payment_terms": "string or null",
  "validity_period": "string or null",
  "additional_notes": "string or null"
}}

Focus on matching quoted items to benchmarks based on name, category, and specifications."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a quotation extraction expert. "
                            "Extract structured data from vendor emails "
                            "and return valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()
            result_json = json.loads(result_text)

            # Build QuotationSummary from JSON
            quoted_items = [
                QuotedItem(**item)
                for item in result_json.get("quoted_items", [])
            ]

            summary = QuotationSummary(
                vendor_name=result_json.get("vendor_name"),
                email_subject=subject,
                summary=result_json.get("summary", ""),
                quoted_items=quoted_items,
                total_items_count=result_json.get("total_items_count", 0),
                matched_benchmarks_count=result_json.get(
                    "matched_benchmarks_count", 0
                ),
                currency=result_json.get("currency", "INR"),
                payment_terms=result_json.get("payment_terms"),
                validity_period=result_json.get("validity_period"),
                additional_notes=result_json.get("additional_notes"),
                extraction_confidence="high",
                extraction_method=(
                    "hybrid" if attachment_data else "openai"
                ),
            )

            return summary

        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            raise ValueError(f"Failed to parse OpenAI response: {e}")
        except Exception as e:
            print(f"OpenAI extraction error: {e}")
            raise

    def extract(
        self,
        email_content: str,
        subject: str = "",
        sender: Optional[str] = None,
        attachments: Optional[list[AttachmentData]] = None,
        benchmarks: Optional[list[BenchmarkItem]] = None,
    ) -> QuotationSummary:
        """
        Extract quotation data from email and attachments.

        Args:
            email_content: Email body content
            subject: Email subject line
            sender: Sender email address
            attachments: List of email attachments
            benchmarks: Available benchmark items for matching

        Returns:
            QuotationSummary with extracted quotation data
        """
        if attachments is None:
            attachments = []
        if benchmarks is None:
            benchmarks = []

        # Extract data from attachments
        attachment_data = self._extract_attachment_data(attachments)

        # Use OpenAI to extract and structure the data
        summary = self._extract_with_openai(
            email_content=email_content,
            subject=subject,
            attachment_data=attachment_data,
            benchmarks=benchmarks,
        )

        return summary


def extract_quotation(
    email_content: str,
    subject: str = "",
    sender: Optional[str] = None,
    attachments: Optional[list[AttachmentData]] = None,
    benchmarks: Optional[list[BenchmarkItem]] = None,
) -> QuotationSummary:
    """
    Extract quotation data (convenience function).

    Args:
        email_content: Email body content
        subject: Email subject line
        sender: Sender email address
        attachments: List of email attachments
        benchmarks: Available benchmark items

    Returns:
        QuotationSummary with extracted data
    """
    extractor = QuotationExtractor()
    return extractor.extract(
        email_content, subject, sender, attachments, benchmarks
    )
