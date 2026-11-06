import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Inception Assistant API")

LLM_URL = os.getenv(
    "LLM_URL",
    "http://llm.inception-dev.svc.cluster.local:8000"
)

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"status": "healthy", "service": "assistant"}

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{LLM_URL}/v1/chat/completions",
                json={
                    "model": "qwen",
                    "messages": [
                        {
                            "role": "user",
                            "content": request.message
                        }
                    ],
                    "max_tokens": 100,
                    "temperature": 0.2
                }
            )
            response.raise_for_status()

            result = response.json()

            return {
                "response": result["choices"][0]["message"]["content"],
                "model": "qwen2.5-0.5b-instruct"
            }

    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="LLM inference failed"
        )
