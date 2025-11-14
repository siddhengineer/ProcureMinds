#!/bin/bash

# Test Email Processing API with cURL

echo "=========================================="
echo "Email Processing API Tests"
echo "=========================================="
echo ""

# Test 1: Intent Classification
echo "Test 1: Intent Classification"
echo "------------------------------------------"
curl -X POST "http://localhost:8000/api/email/classify-intent" \
  -H "Content-Type: application/json" \
  -d '{
    "email_content": "Please send us a quotation for 500 bags of OPC 53 Grade Cement and 10 cubic meters of river sand. We need delivery within 7 days.",
    "subject": "Request for Quotation - Construction Materials"
  }' | python -m json.tool

echo ""
echo ""

# Test 2: Quotation Extraction
echo "Test 2: Quotation Extraction"
echo "------------------------------------------"
curl -X POST "http://localhost:8000/api/email/extract-quotation" \
  -H "Content-Type: application/json" \
  -d '{
    "email_content": "Dear Customer,\n\nThank you for your inquiry. Our quotation:\n\n1. OPC 53 Grade Cement - Rs. 350 per bag\n   Quantity: 500 bags\n   Total: Rs. 175,000\n   Delivery: 7 days\n\n2. River Sand - Rs. 1,200 per m3\n   Quantity: 10 m3\n   Total: Rs. 12,000\n   Delivery: 5 days\n\nPayment Terms: 50% advance, 50% on delivery\nValidity: 15 days\n\nBest regards,\nABC Suppliers",
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
        "notes": "50kg bags"
      },
      {
        "id": 2,
        "name": "River Sand",
        "category": "sand",
        "quality_standard": "Fine Grade",
        "unit": "m3",
        "notes": "Washed river sand"
      }
    ]
  }' | python -m json.tool

echo ""
echo ""

# Test 3: Complete Workflow
echo "Test 3: Complete Workflow"
echo "------------------------------------------"
curl -X POST "http://localhost:8000/api/email/process-complete" \
  -H "Content-Type: application/json" \
  -d '{
    "email_content": "We are pleased to quote:\n\nCement OPC 53: Rs. 340/bag (500 bags)\nFine Sand: Rs. 1,150/m3 (20 m3)\n\nDelivery: 1 week\nPayment: 30% advance",
    "subject": "Quotation - Materials",
    "sender": "vendor@example.com",
    "attachments": null
  }' | python -m json.tool

echo ""
echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="
