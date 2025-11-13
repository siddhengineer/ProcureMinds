from fastapi import FastAPI

from app.api.routers import workflow
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ProcureMinds", version="0.1.0")

app.include_router(workflow.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "ProcureMinds API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
