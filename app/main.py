from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import workflow, auth, project
from app.api import gmail
from app.core.database import Base, engine
from app.core.config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ProcureMinds", version="0.1.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(project.router, prefix="/api")
app.include_router(workflow.router, prefix="/api")
app.include_router(gmail.router, prefix="/api") 


@app.get("/")
def root():
    return {"message": "ProcureMinds API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
