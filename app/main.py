import os
from typing import Optional

import uvicorn
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

app = FastAPI(title="Mini LLM Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Svelte's default dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

start_time = time.time()

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("MODEL", "openai/gpt-4.1-mini")
MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "400"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "80"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


class ChatRequest(BaseModel):
    prompt: str
    temperature: float = 0.1
    max_tokens: Optional[int] = None


def truncate_prompt(prompt: str, max_chars: int = MAX_PROMPT_CHARS) -> str:
    text = prompt.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


async def generate_response(prompt: str, temperature: float, max_tokens: Optional[int] = None):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY is not set")

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Answer briefly and directly."},
                {"role": "user", "content": truncate_prompt(prompt)},
            ],
            temperature=min(max(temperature, 0.0), 0.7),
            timeout=REQUEST_TIMEOUT,
        )
        print(completion.choices[0].message)
        print(completion.choices[0].finish_reason)
        return completion.choices[0].message.content or ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: ChatRequest):
    response = await generate_response(request.prompt, request.temperature, request.max_tokens)
    return {"response": response, "model": MODEL}


@app.get("/health")
async def health():
    """Basic health endpoint showing service status and uptime (seconds)."""
    uptime = int(time.time() - start_time)
    return {"status": "ok", "uptime": uptime}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
