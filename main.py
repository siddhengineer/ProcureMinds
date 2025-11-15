from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import imap_router, quotation_router, rfq_router
from app.api.routers import summary_router  # Add this import
from app.core.config import settings
import logging
from dotenv import load_dotenv

from app.api.routers.workflow import router as workflow_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="ProcureMinds API",
    description="API for ProcureMinds application",
    version="1.0.0"
)

# Include routers
app.include_router(imap_router.router, tags=["IMAP Email"])
app.include_router(quotation_router.router, prefix="/quotations", tags=["Quotations"])
app.include_router(rfq_router.router, prefix="/rfq", tags=["RFQ"])
app.include_router(workflow_router, prefix="/api/workflows")
app.include_router(summary_router.router, prefix="/summary", tags=["Summary"])  # Add this line

@app.get("/")
def root():
    return {"message": "Welcome to ProcureMinds API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
