from fastapi import FastAPI
from routes.extract import router as extract_router

app = FastAPI(title="Call-to-Audit Intelligence API")
app.include_router(extract_router, prefix="/extract")