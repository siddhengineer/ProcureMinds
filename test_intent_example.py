"""
Example usage of the Email Intent Classification Service
"""

from app.services.intent import classify_email_intent, IntentClassifier, EmailIntent


def test_examples():
    """Test the intent classifier with various email examples"""
    
    # Example 1: Clear quotation request
    email1 = """
    Hi,
    
    We are interested in purchasing 500 units of your product.
    Could you please provide us with a quotation for the same?
    
    Best regards,
    John
    """
    
    result1 = classify_email_intent(email1, "Request for Quotation")
    print("Example 1 - Quotation Request:")
    print(f"  Intent: {result1['intent']}")
    print(f"  Confidence: {result1['confidence']}")
    print(f"  Method: {result1['method']}")
    print(f"  Should Process: {result1['should_process']}")
    print()
    
    # Example 2: Casual greeting
    email2 = """
    Hello,
    
    Thank you for your email. Have a great day!
    
    Regards,
    Sarah
    """
    
    result2 = classify_email_intent(email2, "Re: Thank you")
    print("Example 2 - Casual Email:")
    print(f"  Intent: {result2['intent']}")
    print(f"  Confidence: {result2['confidence']}")
    print(f"  Method: {result2['method']}")
    print(f"  Should Process: {result2['should_process']}")
    print()
    
    # Example 3: Pricing inquiry
    email3 = """
    Dear Team,
    
    What are your rates for bulk orders? We need pricing information
    for approximately 1000 units. Please send us your best price.
    
    Thanks,
    Mike
    """
    
    result3 = classify_email_intent(email3, "Pricing Inquiry")
    print("Example 3 - Pricing Inquiry:")
    print(f"  Intent: {result3['intent']}")
    print(f"  Confidence: {result3['confidence']}")
    print(f"  Method: {result3['method']}")
    print(f"  Should Process: {result3['should_process']}")
    print()
    
    # Example 4: Using the classifier directly for multiple emails
    classifier = IntentClassifier()
    
    email4 = "Can you send me an estimate for the project we discussed?"
    result4 = classifier.classify(email4, "Project Estimate")
    
    print("Example 4 - Estimate Request:")
    print(f"  Intent: {result4['intent']}")
    print(f"  Confidence: {result4['confidence']}")
    print(f"  Method: {result4['method']}")
    print(f"  Should Process: {result4['should_process']}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Email Intent Classification Examples")
    print("=" * 60)
    print()
    
    test_examples()
    
    print("=" * 60)
    print("Classification Complete!")
    print("=" * 60)
