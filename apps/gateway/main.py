import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Inception API Gateway")

CATALOG_URL = os.getenv(
    "CATALOG_URL",
    "http://catalog.inception-dev.svc.cluster.local"
)

ASSISTANT_URL = os.getenv(
    "ASSISTANT_URL",
    "http://assistant.inception-dev.svc.cluster.local"
)

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"status": "healthy", "service": "gateway"}

@app.get("/catalog/items")
async def catalog_items():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{CATALOG_URL}/items")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Catalog unavailable"
        )

@app.post("/assistant/chat")
async def assistant_chat(request: ChatRequest):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{ASSISTANT_URL}/chat",
                json={"message": request.message}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Assistant unavailable"
        )
