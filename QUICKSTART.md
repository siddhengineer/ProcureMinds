# Quick Start Guide - Email Processing System

## Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements_email_processing.txt
```

### 2. Configure Environment
Create/update `.env` file:
```env
OPENAI_API_KEY=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
DB_HOST=database-3.cnemo4sc6e40.eu-north-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=postgres_1
DB_USER=postgres_1
DB_PASSWORD=Pratik_6522
```

### 3. Start Server
```bash
uvicorn app.main:app --reload
```

Server runs at: `http://localhost:8000`

## Test the System

### Option 1: Run Test Script
```bash
python test_email_processing.py
```

### Option 2: Run Examples
```bash
python example_quotation_processing.py
```

### Option 3: Use API Directly

**Test Intent Classification:**
```bash
curl -X POST "http://localhost:8000/api/email/classify-intent" \
  -H "Content-Type: application/json" \
  -d '{
    "email_content": "Please send quotation for 500 bags of cement",
    "subject": "RFQ - Cement"
  }'
```

**Test Quotation Extraction:**
```bash
curl -X POST "http://localhost:8000/api/email/extract-quotation" \
  -H "Content-Type: application/json" \
  -d '{
    "email_content": "OPC 53 Cement: Rs. 350/bag. River Sand: Rs. 1200/m3",
    "subject": "Quotation",
    "sender": "vendor@example.com",
    "attachments": [],
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
  }'
```

## API Endpoints

### 1. Intent Classification
```
POST /api/email/classify-intent
```
Classifies email as QUOTATION, QUOTATION_QUERIES, or CASUAL

### 2. Quotation Extraction
```
POST /api/email/extract-quotation
```
Extracts structured quotation data with benchmark matching

### 3. Complete Workflow
```
POST /api/email/process-complete
```
Runs both intent classification and quotation extraction

## View API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
app/
├── schemas/
│   ├── intent.py          # Intent classification schemas
│   └── quotation.py       # Quotation extraction schemas
├── services/
│   ├── intent.py          # Intent classification service
│   └── email_extraction.py # Quotation extraction service
├── workflows/
│   ├── intent_node.py     # Intent LangGraph node
│   ├── quotation_node.py  # Quotation LangGraph node
│   └── complete_email_workflow.py # Complete workflow
└── api/
    └── routers/
        └── email_processing.py # API endpoints
```

## Key Features

✅ **Intent Classification**: Automatically identifies quotation emails
✅ **Quotation Extraction**: Extracts items, prices, terms from emails
✅ **Attachment Support**: Processes Excel and PDF files
✅ **Benchmark Matching**: Matches quoted items to database benchmarks
✅ **LangGraph Integration**: Workflow orchestration with routing
✅ **RESTful API**: Easy integration with FastAPI endpoints

## Next Steps

1. Add your benchmark data to the database
2. Test with real vendor emails
3. Integrate with email fetching service
4. Customize extraction prompts for your use case
5. Add vendor comparison logic

## Troubleshooting

**Server won't start**: Check if port 8000 is available
**OpenAI errors**: Verify OPENAI_API_KEY in .env
**Database errors**: Check database credentials
**Import errors**: Run `pip install -r requirements_email_processing.txt`

## Support

- Full documentation: `EMAIL_PROCESSING_README.md`
- Intent classification: `INTENT_CLASSIFICATION_README.md`
- Examples: `example_quotation_processing.py`
- Tests: `test_email_processing.py`
