"""
Email Intent Classification Service.

Classifies emails into three categories:
- QUOTATION: Emails requesting or discussing quotations/pricing
- QUOTATION_QUERIES: Follow-up questions about quotations (reserved)
- CASUAL: General conversation, greetings, or unrelated content (ignored)

Only QUOTATION emails are passed to the next processing node.

This module follows PEP8 standards and integrates with LangGraph workflows.
"""

import os
import re
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from app.schemas.intent import (
    EmailInput,
    EmailIntent,
    IntentClassificationResult,
)

load_dotenv()


class IntentClassifier:
    """Classifies email intent using OpenAI with keyword fallback."""

    # Keywords for quotation detection
    QUOTATION_KEYWORDS = [
        r'\bquote\b',
        r'\bquotation\b',
        r'\bpricing\b',
        r'\bprice\b',
        r'\bcost\b',
        r'\bestimate\b',
        r'\bproposal\b',
        r'\bbid\b',
        r'\brate\b',
        r'\brates\b',
        r'\bhow much\b',
        r'\bbudget\b',
        r'\bpurchase\b',
        r'\border\b',
        r'\bbuy\b',
        r'\bprocurement\b',
        r'\brfq\b',
        r'\brequest for quote\b',
        r'\bquotation request\b',
    ]

    # Keywords for quotation queries (future use)
    QUERY_KEYWORDS = [
        r'\bfollow.?up\b',
        r'\bquestion about\b',
        r'\bclarification\b',
        r'\bregarding.*quote\b',
        r'\babout.*quotation\b',
        r'\bprevious.*quote\b',
        r'\bearlier.*quotation\b',
    ]

    # Casual/greeting patterns
    CASUAL_KEYWORDS = [
        r'\bhello\b',
        r'\bhi\b',
        r'\bhey\b',
        r'\bgreetings\b',
        r'\bhow are you\b',
        r'\bthanks\b',
        r'\bthank you\b',
        r'\bregards\b',
        r'\bcheers\b',
        r'\bhave a\b',
    ]

    def __init__(self) -> None:
        """Initialize the classifier with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables"
            )

        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Cost-effective model

    def _keyword_match(self, text: str) -> Optional[EmailIntent]:
        """
        Fallback keyword-based classification.

        Args:
            text: Email content to classify

        Returns:
            EmailIntent if confident match found, None otherwise
        """
        text_lower = text.lower()

        # Check for quotation keywords
        quotation_matches = sum(
            1
            for pattern in self.QUOTATION_KEYWORDS
            if re.search(pattern, text_lower, re.IGNORECASE)
        )

        # Check for query keywords
        query_matches = sum(
            1
            for pattern in self.QUERY_KEYWORDS
            if re.search(pattern, text_lower, re.IGNORECASE)
        )

        # Check for casual keywords
        casual_matches = sum(
            1
            for pattern in self.CASUAL_KEYWORDS
            if re.search(pattern, text_lower, re.IGNORECASE)
        )

        # Decision logic: require at least 2 keyword matches
        if quotation_matches >= 2:
            return EmailIntent.QUOTATION
        elif query_matches >= 2 and quotation_matches >= 1:
            return EmailIntent.QUOTATION_QUERIES
        elif casual_matches >= 2 and quotation_matches == 0:
            return EmailIntent.CASUAL

        return None

    def _classify_with_openai(
        self, email_content: str, subject: str = ""
    ) -> EmailIntent:
        """
        Classify email intent using OpenAI.

        Args:
            email_content: The body of the email
            subject: Email subject line (optional)

        Returns:
            EmailIntent classification
        """
        prompt = f"""You are an expert email classifier for a business.
Analyze the following email and classify its intent into ONE category:

1. QUOTATION - Emails requesting pricing, quotes, estimates, proposals,
   or discussing purchase/procurement
2. QUOTATION_QUERIES - Follow-up questions or clarifications about
   existing quotations
3. CASUAL - General greetings, thank you messages, casual conversation,
   or unrelated content

Email Subject: {subject}

Email Content:
{email_content}

Respond with ONLY ONE WORD: "QUOTATION", "QUOTATION_QUERIES", or "CASUAL".
Focus on the primary intent. If the email requests pricing or a quote,
classify as QUOTATION even if it contains greetings."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise email intent classifier. "
                            "Respond with only one word: QUOTATION, "
                            "QUOTATION_QUERIES, or CASUAL."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=10,
            )

            result = response.choices[0].message.content.strip().upper()

            # Map response to enum
            if "QUOTATION_QUERIES" in result:
                return EmailIntent.QUOTATION_QUERIES
            elif "QUOTATION" in result:
                return EmailIntent.QUOTATION
            elif "CASUAL" in result:
                return EmailIntent.CASUAL
            else:
                # Default to casual if unclear
                return EmailIntent.CASUAL

        except Exception as e:
            print(f"OpenAI classification error: {e}")
            raise

    def classify(
        self,
        email_content: str,
        subject: str = "",
        use_fallback: bool = True,
    ) -> IntentClassificationResult:
        """
        Classify email intent with OpenAI and keyword fallback.

        Args:
            email_content: The body of the email
            subject: Email subject line (optional)
            use_fallback: Whether to use keyword matching as fallback

        Returns:
            IntentClassificationResult with intent, confidence, method,
            and should_process flag
        """
        if not email_content or not email_content.strip():
            return IntentClassificationResult(
                intent=EmailIntent.CASUAL,
                confidence="high",
                method="empty_check",
                should_process=False,
            )

        # Try OpenAI classification first
        try:
            intent = self._classify_with_openai(email_content, subject)
            return IntentClassificationResult(
                intent=intent,
                confidence="high",
                method="openai",
                should_process=intent == EmailIntent.QUOTATION,
            )
        except Exception as e:
            print(f"OpenAI classification failed: {e}")

            # Fallback to keyword matching if enabled
            if use_fallback:
                keyword_intent = self._keyword_match(
                    email_content + " " + subject
                )

                if keyword_intent:
                    return IntentClassificationResult(
                        intent=keyword_intent,
                        confidence="medium",
                        method="keyword",
                        should_process=(
                            keyword_intent == EmailIntent.QUOTATION
                        ),
                    )

            # Ultimate fallback: classify as casual
            return IntentClassificationResult(
                intent=EmailIntent.CASUAL,
                confidence="low",
                method="fallback",
                should_process=False,
            )



def classify_email_intent(
    email_content: str, subject: str = ""
) -> IntentClassificationResult:
    """
    Classify email intent (convenience function).

    Args:
        email_content: The body of the email
        subject: Email subject line (optional)

    Returns:
        IntentClassificationResult with classification details
    """
    classifier = IntentClassifier()
    return classifier.classify(email_content, subject)
