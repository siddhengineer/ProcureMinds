from fastapi import FastAPI
import uvicorn

from app.api.routers.workflow import router as workflow_router

app = FastAPI(title="ProcureMinds API")

app.include_router(workflow_router, prefix="/api/workflows")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)