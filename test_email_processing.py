"""Test script for email processing endpoints."""

import asyncio
import json

import httpx


BASE_URL = "http://localhost:8000/api/email"


async def test_intent_classification():
    """Test intent classification endpoint."""
    print("=" * 70)
    print("Test 1: Intent Classification")
    print("=" * 70)

    email_data = {
        "email_content": """
        Dear Sales Team,
        
        We are interested in purchasing the following items:
        - 500 bags of OPC 53 Grade Cement
        - 10 cubic meters of River Sand
        - 5 cubic meters of 20mm Gravel
        
        Please provide your best quotation with delivery terms.
        
        Best regards,
        John Smith
        """,
        "subject": "Request for Quotation - Construction Materials",
        "sender": "john@construction.com",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/classify-intent", json=email_data, timeout=30.0
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Intent: {result['intent']}")
            print(f"Confidence: {result['confidence']}")
            print(f"Method: {result['method']}")
            print(f"Should Process: {result['should_process']}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    print()


async def test_quotation_extraction():
    """Test quotation extraction endpoint."""
    print("=" * 70)
    print("Test 2: Quotation Extraction")
    print("=" * 70)

    extraction_data = {
        "email_content": """
        Dear Customer,
        
        Thank you for your inquiry. Please find our quotation below:
        
        1. OPC 53 Grade Cement - Rs. 350 per bag
           Quantity: 500 bags
           Total: Rs. 175,000
           Delivery: 7 days
        
        2. River Sand (Fine Grade) - Rs. 1,200 per cubic meter
           Quantity: 10 m3
           Total: Rs. 12,000
           Delivery: 5 days
        
        3. 20mm Gravel - Rs. 1,500 per cubic meter
           Quantity: 5 m3
           Total: Rs. 7,500
           Delivery: 5 days
        
        Grand Total: Rs. 194,500
        Payment Terms: 50% advance, 50% on delivery
        Validity: 15 days
        
        Best regards,
        ABC Suppliers
        """,
        "subject": "Re: Quotation for Construction Materials",
        "sender": "sales@abcsuppliers.com",
        "attachments": [],
        "benchmarks": [
            {
                "id": 1,
                "name": "OPC 53 Grade Cement",
                "category": "cement",
                "quality_standard": "IS 12269",
                "unit": "bags",
                "notes": "50kg bags",
            },
            {
                "id": 2,
                "name": "River Sand",
                "category": "sand",
                "quality_standard": "Fine Grade",
                "unit": "m3",
                "notes": "Washed river sand",
            },
            {
                "id": 3,
                "name": "20mm Gravel",
                "category": "gravel",
                "quality_standard": "IS 383",
                "unit": "m3",
                "notes": "Crushed stone aggregate",
            },
        ],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/extract-quotation",
            json=extraction_data,
            timeout=60.0,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Vendor: {result.get('vendor_name', 'N/A')}")
            print(f"Summary: {result['summary']}")
            print(f"\nQuoted Items: {result['total_items_count']}")
            print(
                f"Matched Benchmarks: {result['matched_benchmarks_count']}"
            )
            print(f"\nItems:")
            for idx, item in enumerate(result["quoted_items"], 1):
                print(f"\n{idx}. {item['item_name']}")
                print(f"   Unit Price: {item.get('unit_price', 'N/A')}")
                print(f"   Quantity: {item.get('quantity', 'N/A')}")
                print(f"   Unit: {item['unit']}")
                print(
                    f"   Matched Benchmark: {item.get('matched_benchmark_id', 'N/A')}"
                )
            print(f"\nPayment Terms: {result.get('payment_terms', 'N/A')}")
            print(f"Validity: {result.get('validity_period', 'N/A')}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    print()


async def test_complete_workflow():
    """Test complete email processing workflow."""
    print("=" * 70)
    print("Test 3: Complete Workflow")
    print("=" * 70)

    workflow_data = {
        "email_content": """
        Dear Team,
        
        We are pleased to quote for your requirements:
        
        - Cement OPC 53: Rs. 340/bag (500 bags available)
        - Fine Sand: Rs. 1,150/m3 (20 m3 available)
        - Coarse Aggregate 20mm: Rs. 1,450/m3 (15 m3 available)
        
        Delivery within 1 week. Payment: 30% advance.
        
        Regards,
        XYZ Materials
        """,
        "subject": "Quotation - Construction Materials",
        "sender": "info@xyzmaterials.com",
        "attachments": None,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/process-complete",
            json=workflow_data,
            timeout=60.0,
        )

        if response.status_code == 200:
            result = response.json()
            print("Workflow Result:")
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    print()


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("EMAIL PROCESSING API TESTS")
    print("=" * 70 + "\n")

    try:
        await test_intent_classification()
        await test_quotation_extraction()
        await test_complete_workflow()

        print("=" * 70)
        print("All tests completed!")
        print("=" * 70)

    except httpx.ConnectError:
        print("\nError: Could not connect to API server.")
        print("Make sure the server is running on http://localhost:8000")
        print("\nStart the server with:")
        print("  uvicorn app.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
