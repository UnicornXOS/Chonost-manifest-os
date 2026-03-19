from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from ..utils.unified_ai_client import get_client

router = APIRouter()

class ChatRequest(BaseModel):
    provider: str
    messages: List[Dict[str, str]]
    model: str = None
    temperature: float = 0.7

@router.post("/chat")
async def chat_with_provider(request: ChatRequest):
    """
    Handles a chat request with a specified AI provider.
    """
    try:
        client = get_client()
        response = await client.generate_response(
            provider=request.provider,
            messages=request.messages,
            model=request.model,
            temperature=request.temperature
        )
        if not response.get('success'):
            raise HTTPException(status_code=500, detail=response.get('error', 'Unknown error'))
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
