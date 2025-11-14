from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import imap_router, quotation_router
from app.core.config import settings
import logging

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

@app.get("/")
def root():
    return {"message": "Welcome to ProcureMinds API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}