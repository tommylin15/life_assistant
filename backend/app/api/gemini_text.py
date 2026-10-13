"""Explicit, signed, read-only Gemini text call for authenticated Life users.

Not a Drive enrichment substitute: no document content is collected here.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import current_user
from app.services.shared_gemini_gateway import GatewayTextError, generate_text

router = APIRouter(prefix="/ai", tags=["ai"])


class TextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=8192)


class TextResponse(BaseModel):
    status: str
    request_id: str
    model: str
    text: str


@router.post("/text", response_model=TextResponse)
async def execute_text(
    body: TextRequest,
    response: Response,
    user: dict = Depends(current_user),
):
    # User has explicitly submitted this prompt; never fetch Google/Drive data,
    # call a background task, or allow a browser-supplied owner/project/model.
    response.headers["Cache-Control"] = "no-store"
    try:
        return await generate_text(body.prompt, user_sub=user["sub"])
    except GatewayTextError as exc:
        # Stable error codes only: never disclose tokens or provider payloads.
        raise HTTPException(exc.status_code, detail=exc.code) from exc
