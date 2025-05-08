from fastapi import FastAPI
from routes.extract import router as extract_router

app = FastAPI(title="Audio-Auditing Intelligence API")
app.include_router(extract_router, prefix="/api/v1")