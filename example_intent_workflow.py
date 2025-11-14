"""
Example usage of Intent Classification Node in LangGraph Workflow.

This demonstrates PEP8-compliant integration of intent classification
with LangGraph for email processing.
"""

import asyncio

from app.workflows.email_workflow import EmailProcessingWorkflow


async def main() -> None:
    """Run example email processing workflow."""
    # Initialize workflow
    workflow = EmailProcessingWorkflow()

    # Example 1: Quotation request email
    print("=" * 70)
    print("Example 1: Quotation Request Email")
    print("=" * 70)

    email1 = """
    Dear Sales Team,

    We are interested in purchasing 500 units of your Model X product.
    Could you please provide us with a detailed quotation including:
    - Unit price for bulk order
    - Delivery timeline
    - Payment terms

    Looking forward to your response.

    Best regards,
    John Smith
    Procurement Manager
    """

    result1 = await workflow.execute(
        email_content=email1,
        subject="Request for Quotation - Model X",
        sender="john.smith@company.com",
    )

    print(f"Intent: {result1['intent']}")
    print(f"Confidence: {result1['confidence']}")
    print(f"Should Process: {result1['processed']}")
    print(f"Quotation Data: {result1['quotation_data']}")
    print()

    # Example 2: Casual email
    print("=" * 70)
    print("Example 2: Casual Email")
    print("=" * 70)

    email2 = """
    Hi there,

    Thank you for your email yesterday. Have a great weekend!

    Cheers,
    Sarah
    """

    result2 = await workflow.execute(
        email_content=email2,
        subject="Re: Thank you",
        sender="sarah@example.com",
    )

    print(f"Intent: {result2['intent']}")
    print(f"Confidence: {result2['confidence']}")
    print(f"Should Process: {result2['processed']}")
    print(f"Quotation Data: {result2['quotation_data']}")
    print()

    # Example 3: Pricing inquiry
    print("=" * 70)
    print("Example 3: Pricing Inquiry")
    print("=" * 70)

    email3 = """
    Hello,

    What are your current rates for enterprise licenses?
    We need pricing for approximately 1000 users.

    Please send your best offer.

    Thanks,
    Mike Johnson
    """

    result3 = await workflow.execute(
        email_content=email3,
        subject="Enterprise Pricing Inquiry",
        sender="mike.j@enterprise.com",
    )

    print(f"Intent: {result3['intent']}")
    print(f"Confidence: {result3['confidence']}")
    print(f"Should Process: {result3['processed']}")
    print(f"Quotation Data: {result3['quotation_data']}")
    print()

    # Example 4: Using standalone intent node
    print("=" * 70)
    print("Example 4: Standalone Intent Classification")
    print("=" * 70)

    from app.services.intent import classify_email_intent

    email4 = "Can you send me an estimate for the project?"
    result4 = classify_email_intent(email4, "Project Estimate")

    print(f"Intent: {result4.intent}")
    print(f"Confidence: {result4.confidence}")
    print(f"Method: {result4.method}")
    print(f"Should Process: {result4.should_process}")
    print()

    print("=" * 70)
    print("All Examples Completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
