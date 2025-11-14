# 🚀 START HERE - Email Processing System

## What You Have

A complete **PEP8-compliant** email processing system with:

1. **Intent Classification Node** - Identifies quotation emails
2. **Quotation Extraction Node** - Extracts structured data from vendor emails
3. **LangGraph Workflow** - Orchestrates both nodes with routing
4. **REST API** - Three endpoints ready to use
5. **Attachment Processing** - Handles Excel and PDF files
6. **Benchmark Matching** - Matches quoted items to database

## Quick Start (3 Steps)

### Step 1: Install Dependencies
```bash
pip install -r requirements_email_processing.txt
```

### Step 2: Start Server
```bash
uvicorn app.main:app --reload
```

### Step 3: Test It
```bash
python test_email_processing.py
```

✅ **Done!** Your system is running at `http://localhost:8000`

## What It Does

### Input: Vendor Email
```
Dear Customer,

OPC 53 Grade Cement - Rs. 350 per bag
Quantity: 500 bags
Delivery: 7 days

Payment: 50% advance
Valid for 15 days

Best regards,
ABC Suppliers
```

### Output: Structured JSON
```json
{
  "intent": "quotation",
  "should_process": true,
  "quotation_summary": {
    "vendor_name": "ABC Suppliers",
    "quoted_items": [
      {
        "item_name": "OPC 53 Grade Cement",
        "quantity": 500,
        "unit": "bags",
        "unit_price": "350.00",
        "delivery_time": "7 days",
        "matched_benchmark_id": 1
      }
    ],
    "payment_terms": "50% advance",
    "validity_period": "15 days"
  }
}
```

## API Endpoints

### 1. Classify Intent
```bash
POST /api/email/classify-intent
```
Determines if email is QUOTATION, CASUAL, or QUERIES

### 2. Extract Quotation
```bash
POST /api/email/extract-quotation
```
Extracts items, prices, terms from quotation emails

### 3. Complete Workflow
```bash
POST /api/email/process-complete
```
Runs both classification and extraction in one call

## Test Options

### Option 1: Python Test Script (Recommended)
```bash
python test_email_processing.py
```

### Option 2: Examples
```bash
python example_quotation_processing.py
```

### Option 3: cURL (Windows)
```bash
test_api_curl.bat
```

### Option 4: API Docs
Open browser: `http://localhost:8000/docs`

## File Structure

```
📁 Your Project
├── 📄 START_HERE.md                    ← You are here
├── 📄 QUICKSTART.md                    ← Quick setup guide
├── 📄 SYSTEM_SUMMARY.md                ← What was built
├── 📄 EMAIL_PROCESSING_README.md       ← Full documentation
│
├── 📁 app/
│   ├── 📁 schemas/
│   │   ├── intent.py                   ← Intent schemas
│   │   └── quotation.py                ← Quotation schemas
│   │
│   ├── 📁 services/
│   │   ├── intent.py                   ← Intent classification
│   │   └── email_extraction.py         ← Quotation extraction
│   │
│   ├── 📁 workflows/
│   │   ├── intent_node.py              ← Intent LangGraph node
│   │   ├── quotation_node.py           ← Quotation LangGraph node
│   │   └── complete_email_workflow.py  ← Complete workflow
│   │
│   └── 📁 api/routers/
│       └── email_processing.py         ← REST API endpoints
│
├── 📄 test_email_processing.py         ← API tests
├── 📄 example_quotation_processing.py  ← Usage examples
└── 📄 requirements_email_processing.txt ← Dependencies
```

## How It Works

```
┌─────────────────┐
│  Vendor Email   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Intent Classification   │ ← Node 1
│ (QUOTATION/CASUAL)      │
└────────┬────────────────┘
         │
         ▼
    [Router]
         │
         ├─ CASUAL → End
         │
         └─ QUOTATION
                │
                ▼
    ┌──────────────────────┐
    │ Quotation Extraction │ ← Node 2
    │ + Benchmark Matching │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────┐
    │  Structured JSON │
    └──────────────────┘
```

## Key Features

✅ **Smart Classification** - OpenAI + keyword fallback
✅ **Data Extraction** - Vendor info, items, prices, terms
✅ **Attachment Support** - Excel (.xlsx) and PDF files
✅ **Benchmark Matching** - Auto-match to database items
✅ **Confidence Scores** - Know how reliable the extraction is
✅ **PEP8 Compliant** - Clean, typed, documented code
✅ **Production Ready** - Error handling, validation, async

## Environment Setup

Your `.env` file already has:
```env
OPENAI_API_KEY=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
DB_HOST=database-3.cnemo4sc6e40.eu-north-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=postgres_1
DB_USER=postgres_1
DB_PASSWORD=Pratik_6522
```

## Next Steps

### Immediate
1. ✅ Run tests: `python test_email_processing.py`
2. ✅ Try examples: `python example_quotation_processing.py`
3. ✅ Check API docs: `http://localhost:8000/docs`

### Integration
1. Connect to your email fetching service
2. Add more benchmarks to database
3. Customize extraction prompts
4. Add vendor comparison logic

### Enhancement
1. Add more attachment formats (CSV, Word)
2. Implement QUOTATION_QUERIES processing
3. Create vendor ranking system
4. Add email notifications

## Documentation

- **Quick Start**: `QUICKSTART.md`
- **Full Docs**: `EMAIL_PROCESSING_README.md`
- **System Summary**: `SYSTEM_SUMMARY.md`
- **Intent Node**: `INTENT_CLASSIFICATION_README.md`

## Troubleshooting

**Server won't start?**
- Check if port 8000 is available
- Try: `uvicorn app.main:app --reload --port 8001`

**OpenAI errors?**
- Verify OPENAI_API_KEY in .env file
- Check API key is valid

**Import errors?**
- Run: `pip install -r requirements_email_processing.txt`

**Database errors?**
- Check database credentials in .env
- Ensure database is accessible

## Support

Need help? Check these files:
1. `QUICKSTART.md` - Setup guide
2. `EMAIL_PROCESSING_README.md` - Full documentation
3. `example_quotation_processing.py` - Code examples
4. `test_email_processing.py` - Test examples

## Success Checklist

- [ ] Dependencies installed
- [ ] Server running
- [ ] Tests passing
- [ ] API docs accessible
- [ ] Examples working

Once all checked, you're ready to process vendor emails! 🎉

## Quick Test

```bash
# Terminal 1: Start server
uvicorn app.main:app --reload

# Terminal 2: Run tests
python test_email_processing.py
```

Expected output: All tests pass with structured JSON responses

---

**You're all set!** Start with `python test_email_processing.py` to see it in action.
