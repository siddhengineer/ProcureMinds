# Email Processing System - Complete Documentation

PEP8-compliant LangGraph workflow for vendor email processing with intent classification and quotation extraction.

## Architecture Overview

```
Email Input
    ↓
Intent Classification Node
    ↓
[Router: QUOTATION/CASUAL/QUERIES]
    ↓
Quotation Extraction Node (if QUOTATION)
    ↓
JSON Output with Benchmark Matching
```

## Components

### 1. Intent Classification Node
**Location**: `app/workflows/intent_node.py`

Classifies emails into:
- **QUOTATION**: Vendor quotations (processed)
- **QUOTATION_QUERIES**: Follow-up questions (reserved)
- **CASUAL**: General emails (ignored)

### 2. Quotation Extraction Node
**Location**: `app/workflows/quotation_node.py`

Extracts structured data from vendor quotations:
- Vendor information
- Quoted items with prices
- Benchmark matching
- Delivery terms
- Payment conditions

### 3. Attachment Processing
**Location**: `app/services/email_extraction.py`

Supports:
- **Excel files** (.xlsx, .xls): Extracts tabular data
- **PDF files**: Extracts text content

### 4. Benchmark Matching

Matches quoted items against database benchmarks:
- Cement (OPC 53, PPC, etc.)
- Sand (River sand, M-sand, etc.)
- Gravel (20mm, 40mm aggregates)
- Tiles (Various sizes and types)

## API Endpoints

### 1. Classify Intent
```http
POST /api/email/classify-intent
```

**Request Body**:
```json
{
  "email_content": "Email body text",
  "subject": "Email subject",
  "sender": "sender@example.com"
}
```

**Response**:
```json
{
  "intent": "quotation",
  "confidence": "high",
  "method": "openai",
  "should_process": true
}
```

### 2. Extract Quotation
```http
POST /api/email/extract-quotation
```

**Request Body**:
```json
{
  "email_content": "Vendor quotation email",
  "subject": "Quotation for materials",
  "sender": "vendor@supplier.com",
  "attachments": [
    {
      "filename": "quotation.xlsx",
      "file_type": "excel",
      "file_path": "/path/to/file.xlsx"
    }
  ],
  "benchmarks": [
    {
      "id": 1,
      "name": "OPC 53 Grade Cement",
      "category": "cement",
      "quality_standard": "IS 12269",
      "unit": "bags",
      "notes": "50kg bags"
    }
  ]
}
```

**Response**:
```json
{
  "vendor_name": "ABC Suppliers",
  "email_subject": "Quotation for materials",
  "summary": "Vendor offering cement, sand, and gravel at competitive prices",
  "quoted_items": [
    {
      "item_name": "OPC 53 Grade Cement",
      "description": "Premium quality cement",
      "quantity": 500,
      "unit": "bags",
      "unit_price": "350.00",
      "total_price": "175000.00",
      "delivery_time": "7 days",
      "specifications": {},
      "matched_benchmark_id": 1,
      "match_confidence": "high"
    }
  ],
  "total_items_count": 3,
  "matched_benchmarks_count": 3,
  "currency": "INR",
  "payment_terms": "50% advance, 50% on delivery",
  "validity_period": "15 days",
  "additional_notes": null,
  "extraction_confidence": "high",
  "extraction_method": "hybrid"
}
```

### 3. Complete Workflow
```http
POST /api/email/process-complete
```

**Request Body**:
```json
{
  "email_content": "Vendor email content",
  "subject": "Quotation",
  "sender": "vendor@example.com",
  "attachments": []
}
```

**Response**: Complete workflow state with intent and quotation data

## Database Schema

### Benchmark Tables

**benchmark_cement**:
- id, name, quality_standard, default_quantity_per_m3, unit, notes

**benchmark_sand**:
- id, name, quality_standard, default_quantity_per_m3, unit, notes

**benchmark_gravel**:
- id, name, quality_standard, default_quantity_per_m3, unit, size_mm, notes

**benchmark_tile**:
- id, name, quality_standard, length_mm, width_mm, default_wastage_multiplier, unit, notes

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements_email_processing.txt
```

### 2. Set Environment Variables
```env
OPENAI_API_KEY=sk-or-v1-your-api-key-here
DB_HOST=your-database-host
DB_PORT=5432
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
```

### 3. Run the Server
```bash
uvicorn app.main:app --reload
```

Server will start at: `http://localhost:8000`

## Testing

### Run Test Script
```bash
python test_email_processing.py
```

### Manual Testing with cURL

**Test Intent Classification**:
```bash
curl -X POST "http://localhost:8000/api/email/classify-intent" \
  -H "Content-Type: application/json" \
  -d '{
    "email_content": "Please send quotation for 500 bags cement",
    "subject": "RFQ - Cement"
  }'
```

**Test Quotation Extraction**:
```bash
curl -X POST "http://localhost:8000/api/email/extract-quotation" \
  -H "Content-Type: application/json" \
  -d @test_quotation.json
```

## Usage Examples

### Python Client
```python
import httpx
import asyncio

async def process_email():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/email/process-complete",
            json={
                "email_content": "Your quotation email here",
                "subject": "Quotation Request",
                "sender": "vendor@example.com"
            }
        )
        return response.json()

result = asyncio.run(process_email())
print(result)
```

### Direct Service Usage
```python
from app.services.intent import classify_email_intent
from app.services.email_extraction import extract_quotation

# Classify intent
intent_result = classify_email_intent(
    email_content="Please quote for cement",
    subject="RFQ"
)

# Extract quotation
quotation_result = extract_quotation(
    email_content="Cement: Rs. 350/bag",
    subject="Quotation",
    benchmarks=[...]
)
```

## Workflow Integration

### Custom LangGraph Workflow
```python
from langgraph.graph import StateGraph, END
from app.workflows.intent_node import IntentClassificationNode
from app.workflows.quotation_node import QuotationExtractionNode

workflow = StateGraph(EmailWorkflowState)
intent_node = IntentClassificationNode()
quotation_node = QuotationExtractionNode()

workflow.add_node("classify", intent_node.classify_intent)
workflow.add_node("extract", quotation_node.extract_quotation)

workflow.set_entry_point("classify")
workflow.add_conditional_edges(
    "classify",
    intent_node.route_based_on_intent,
    {
        "quotation_processing": "extract",
        "end": END
    }
)
workflow.add_edge("extract", END)

graph = workflow.compile()
result = await graph.ainvoke(initial_state)
```

## Features

✅ **PEP8 Compliant**: Full type hints, docstrings, proper formatting
✅ **Schema-Based**: Pydantic models for validation
✅ **LangGraph Integration**: Async nodes with state management
✅ **Attachment Support**: Excel and PDF extraction
✅ **Benchmark Matching**: Automatic matching with confidence scores
✅ **OpenAI Powered**: Intelligent extraction with GPT-4o-mini
✅ **Error Handling**: Graceful fallbacks and error messages
✅ **RESTful API**: FastAPI endpoints for easy integration

## Output Format

The quotation extraction returns structured JSON:

```json
{
  "vendor_name": "Vendor name from email",
  "email_subject": "Email subject line",
  "summary": "Natural language summary",
  "quoted_items": [
    {
      "item_name": "Product name",
      "quantity": 100,
      "unit": "bags",
      "unit_price": "350.00",
      "total_price": "35000.00",
      "delivery_time": "7 days",
      "matched_benchmark_id": 1,
      "match_confidence": "high"
    }
  ],
  "total_items_count": 5,
  "matched_benchmarks_count": 4,
  "currency": "INR",
  "payment_terms": "Payment terms",
  "validity_period": "Validity period",
  "extraction_confidence": "high"
}
```

## Next Steps

1. Add more attachment formats (CSV, Word documents)
2. Implement query processing for QUOTATION_QUERIES
3. Add vendor comparison logic
4. Create vendor ranking system
5. Add email notification system
6. Implement audit logging
7. Add unit tests and integration tests

## Troubleshooting

**OpenAI API Error**: Check OPENAI_API_KEY in .env file
**Database Connection Error**: Verify database credentials
**Attachment Processing Error**: Ensure pandas and PyPDF2 are installed
**Import Errors**: Run `pip install -r requirements_email_processing.txt`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
