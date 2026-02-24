from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import leads_router, sales_router

app = FastAPI(
    title="CRM Leads Service",
    description="Lead management with AI-powered analysis via Claude API",
    version="1.0.0",
)

app.include_router(leads_router)
app.include_router(sales_router)


@app.get("/health", tags=["Health"])
async def health():
    return JSONResponse({"status": "ok"})
