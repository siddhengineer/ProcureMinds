@echo off
REM Test Email Processing API with cURL (Windows)

echo ==========================================
echo Email Processing API Tests
echo ==========================================
echo.

REM Test 1: Intent Classification
echo Test 1: Intent Classification
echo ------------------------------------------
curl -X POST "http://localhost:8000/api/email/classify-intent" ^
  -H "Content-Type: application/json" ^
  -d "{\"email_content\": \"Please send us a quotation for 500 bags of OPC 53 Grade Cement\", \"subject\": \"RFQ\"}"

echo.
echo.

REM Test 2: Simple Quotation Extraction
echo Test 2: Quotation Extraction
echo ------------------------------------------
curl -X POST "http://localhost:8000/api/email/extract-quotation" ^
  -H "Content-Type: application/json" ^
  -d "{\"email_content\": \"OPC 53 Cement: Rs. 350/bag. River Sand: Rs. 1200/m3\", \"subject\": \"Quotation\", \"sender\": \"vendor@example.com\", \"attachments\": [], \"benchmarks\": [{\"id\": 1, \"name\": \"OPC 53 Grade Cement\", \"category\": \"cement\", \"quality_standard\": \"IS 12269\", \"unit\": \"bags\", \"notes\": \"50kg bags\"}]}"

echo.
echo.

echo ==========================================
echo Tests completed!
echo ==========================================
echo.
echo For better formatted output, use Python test script:
echo   python test_email_processing.py
echo.
pause
