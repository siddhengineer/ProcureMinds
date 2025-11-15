from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import imap_router, quotation_router, rfq_router
from app.api.routers import summary_router  # Add this import
from app.api.routers import vendor_router
from app.api.routers import rfq_email_router
from app.core.config import settings
import logging
from dotenv import load_dotenv
import uvicorn

from app.api.routers import workflow, auth, project, boq, imap_router, quotation_router, rfq_router
from app.api import gmail
from app.core.database import Base, engine
from app.core.config import settings
from app.api.routers.workflow import router as workflow_router
 

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ProcureMinds API",
    description="API for ProcureMinds application",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(imap_router.router, tags=["IMAP Email"])
app.include_router(quotation_router.router, prefix="/quotations", tags=["Quotations"])
app.include_router(rfq_router.router, prefix="/rfq", tags=["RFQ"])
app.include_router(workflow_router, prefix="/api/workflows")
app.include_router(summary_router.router, prefix="/summary", tags=["Summary"])  # Add this line
app.include_router(vendor_router.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(project.router, prefix="/api")
app.include_router(boq.router, prefix="/api")
app.include_router(workflow.router, prefix="/api")
app.include_router(gmail.router, prefix="/api")
app.include_router(imap_router.router, prefix="/api", tags=["IMAP Email"])
app.include_router(quotation_router.router, prefix="/api/quotations", tags=["Quotations"])
app.include_router(rfq_router.router, prefix="/api/rfq", tags=["RFQ"])

app.include_router(workflow_router, prefix="/api/workflows")
app.include_router(rfq_email_router.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Welcome to ProcureMinds API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
