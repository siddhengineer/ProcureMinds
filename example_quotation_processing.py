"""Example: Complete Email Quotation Processing."""

import asyncio

from app.schemas.quotation import AttachmentData, BenchmarkItem
from app.services.email_extraction import extract_quotation
from app.services.intent import classify_email_intent


async def example_1_simple_quotation():
    """Example 1: Simple quotation without attachments."""
    print("=" * 70)
    print("Example 1: Simple Vendor Quotation")
    print("=" * 70)

    email = """
    Dear Customer,
    
    Thank you for your inquiry. Our quotation:
    
    1. OPC 53 Grade Cement - Rs. 350 per bag
       Quantity: 500 bags
       Delivery: 7 days
    
    2. River Sand - Rs. 1,200 per m3
       Quantity: 10 m3
       Delivery: 5 days
    
    Payment: 50% advance, 50% on delivery
    Valid for 15 days
    
    Best regards,
    ABC Suppliers
    """

    # Step 1: Classify intent
    intent = classify_email_intent(email, "Quotation - Construction Materials")
    print(f"Intent: {intent.intent}")
    print(f"Should Process: {intent.should_process}\n")

    if intent.should_process:
        # Step 2: Extract quotation
        benchmarks = [
            BenchmarkItem(
                id=1,
                name="OPC 53 Grade Cement",
                category="cement",
                quality_standard="IS 12269",
                unit="bags",
            ),
            BenchmarkItem(
                id=2,
                name="River Sand",
                category="sand",
                quality_standard="Fine Grade",
                unit="m3",
            ),
        ]

        result = extract_quotation(
            email_content=email,
            subject="Quotation - Construction Materials",
            sender="sales@abcsuppliers.com",
            benchmarks=benchmarks,
        )

        print(f"Vendor: {result.vendor_name}")
        print(f"Summary: {result.summary}")
        print(f"\nItems Quoted: {result.total_items_count}")
        print(f"Matched Benchmarks: {result.matched_benchmarks_count}")
        print(f"\nQuoted Items:")
        for item in result.quoted_items:
            print(f"  - {item.item_name}")
            print(f"    Price: {item.unit_price} per {item.unit}")
            print(f"    Quantity: {item.quantity}")
            print(f"    Benchmark Match: {item.matched_benchmark_id}")
        print(f"\nPayment Terms: {result.payment_terms}")
        print(f"Validity: {result.validity_period}")

    print()


async def example_2_detailed_quotation():
    """Example 2: Detailed quotation with specifications."""
    print("=" * 70)
    print("Example 2: Detailed Quotation with Specifications")
    print("=" * 70)

    email = """
    Subject: Quotation for Construction Materials - Project XYZ
    
    Dear Sir/Madam,
    
    We are pleased to submit our quotation for your project:
    
    ITEM 1: Portland Pozzolana Cement (PPC)
    - Brand: UltraTech
    - Grade: PPC
    - Packaging: 50kg bags
    - Rate: Rs. 340 per bag
    - Minimum Order: 200 bags
    - Delivery: Within 5 working days
    
    ITEM 2: M-Sand (Manufactured Sand)
    - Type: Crushed granite
    - Size: 0-4.75mm
    - Rate: Rs. 1,100 per cubic meter
    - Available Quantity: 50 m3
    - Delivery: 3-4 days
    
    ITEM 3: 20mm Coarse Aggregate
    - Type: Crushed stone
    - Size: 20mm nominal
    - Rate: Rs. 1,450 per m3
    - Quality: Conforming to IS 383
    - Delivery: 3-4 days
    
    ITEM 4: Vitrified Tiles
    - Size: 600x600mm
    - Finish: Glossy
    - Rate: Rs. 45 per sq.ft
    - Wastage: 10% recommended
    - Delivery: 10-12 days
    
    TERMS & CONDITIONS:
    - Payment: 30% advance, balance before delivery
    - Prices valid for 30 days
    - GST extra as applicable
    - Transportation charges extra
    
    For bulk orders, special discounts available.
    
    Best Regards,
    XYZ Building Materials
    Contact: 9876543210
    """

    benchmarks = [
        BenchmarkItem(
            id=1,
            name="PPC Cement",
            category="cement",
            quality_standard="IS 1489",
            unit="bags",
            notes="50kg bags",
        ),
        BenchmarkItem(
            id=2,
            name="M-Sand",
            category="sand",
            quality_standard="IS 383",
            unit="m3",
            notes="Manufactured sand",
        ),
        BenchmarkItem(
            id=3,
            name="20mm Gravel",
            category="gravel",
            quality_standard="IS 383",
            unit="m3",
            notes="Coarse aggregate",
        ),
        BenchmarkItem(
            id=4,
            name="Vitrified Tiles 600x600",
            category="tile",
            quality_standard="IS 15622",
            unit="m2",
            notes="Glossy finish",
        ),
    ]

    result = extract_quotation(
        email_content=email,
        subject="Quotation for Construction Materials",
        sender="sales@xyzmaterials.com",
        benchmarks=benchmarks,
    )

    print(f"Vendor: {result.vendor_name}")
    print(f"Currency: {result.currency}")
    print(f"\nSummary:\n{result.summary}")
    print(f"\nExtraction Method: {result.extraction_method}")
    print(f"Confidence: {result.extraction_confidence}")
    print(f"\nTotal Items: {result.total_items_count}")
    print(f"Matched to Benchmarks: {result.matched_benchmarks_count}")

    print("\n" + "-" * 70)
    print("DETAILED ITEM BREAKDOWN")
    print("-" * 70)

    for idx, item in enumerate(result.quoted_items, 1):
        print(f"\n{idx}. {item.item_name}")
        print(f"   Description: {item.description or 'N/A'}")
        print(f"   Unit Price: Rs. {item.unit_price} per {item.unit}")
        if item.quantity:
            print(f"   Quantity: {item.quantity} {item.unit}")
        if item.total_price:
            print(f"   Total: Rs. {item.total_price}")
        print(f"   Delivery: {item.delivery_time or 'Not specified'}")
        print(
            f"   Benchmark Match: ID {item.matched_benchmark_id} "
            f"({item.match_confidence or 'N/A'} confidence)"
        )

    print("\n" + "-" * 70)
    print(f"Payment Terms: {result.payment_terms}")
    print(f"Validity: {result.validity_period}")
    if result.additional_notes:
        print(f"Notes: {result.additional_notes}")

    print()


async def example_3_comparison():
    """Example 3: Compare multiple vendor quotations."""
    print("=" * 70)
    print("Example 3: Vendor Comparison")
    print("=" * 70)

    vendors = [
        {
            "name": "Vendor A",
            "email": """
            OPC 53 Cement: Rs. 350/bag (500 bags)
            River Sand: Rs. 1,200/m3 (10 m3)
            Delivery: 7 days
            Payment: 50% advance
            """,
        },
        {
            "name": "Vendor B",
            "email": """
            OPC 53 Grade Cement: Rs. 340/bag (1000 bags available)
            Fine River Sand: Rs. 1,150/m3 (20 m3 available)
            Delivery: 5 days
            Payment: 30% advance
            """,
        },
        {
            "name": "Vendor C",
            "email": """
            Portland Cement OPC 53: Rs. 355/bag
            River Sand (washed): Rs. 1,250/m3
            Delivery: 10 days
            Payment: Full advance
            """,
        },
    ]

    benchmarks = [
        BenchmarkItem(
            id=1,
            name="OPC 53 Grade Cement",
            category="cement",
            quality_standard="IS 12269",
            unit="bags",
        ),
        BenchmarkItem(
            id=2,
            name="River Sand",
            category="sand",
            quality_standard="Fine Grade",
            unit="m3",
        ),
    ]

    results = []
    for vendor in vendors:
        result = extract_quotation(
            email_content=vendor["email"],
            subject=f"Quotation from {vendor['name']}",
            benchmarks=benchmarks,
        )
        results.append({"vendor": vendor["name"], "data": result})

    # Compare results
    print("\nVENDOR COMPARISON")
    print("-" * 70)

    for res in results:
        print(f"\n{res['vendor']}:")
        data = res["data"]
        print(f"  Items Quoted: {data.total_items_count}")
        print(f"  Matched Benchmarks: {data.matched_benchmarks_count}")

        for item in data.quoted_items:
            print(
                f"  - {item.item_name}: Rs. {item.unit_price}/{item.unit}"
            )

        print(f"  Payment: {data.payment_terms or 'Not specified'}")

    print("\n" + "=" * 70)


async def main():
    """Run all examples."""
    await example_1_simple_quotation()
    await example_2_detailed_quotation()
    await example_3_comparison()

    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
