"""Refine endpoint — direct LLM text refinement without the chat flow."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm_service import llm_service

router = APIRouter(prefix="/api", tags=["refine"])


class RefineRequest(BaseModel):
    full_text: str
    selected_text: str = ""
    instruction: str


class RefineResponse(BaseModel):
    refined_text: str


@router.post("/refine", response_model=RefineResponse)
async def refine_text(request: RefineRequest):
    """
    Refine text based on an instruction. Returns the complete updated text
    with only the targeted portion changed.
    Called directly by the text editor iframe — no chat messages involved.
    """
    if request.selected_text:
        prompt = (
            f"You are a text editor assistant. The user has selected a portion of their text "
            f"and wants you to refine ONLY that portion based on their instruction.\n\n"
            f"FULL TEXT:\n{request.full_text}\n\n"
            f"SELECTED PORTION TO REFINE:\n{request.selected_text}\n\n"
            f"INSTRUCTION: {request.instruction}\n\n"
            f"Return the COMPLETE text with ONLY the selected portion modified. "
            f"Keep everything else exactly the same. "
            f"Return ONLY the final text, no explanations or markdown formatting."
        )
    else:
        prompt = (
            f"You are a text editor assistant. Refine the following text based on the instruction.\n\n"
            f"TEXT:\n{request.full_text}\n\n"
            f"INSTRUCTION: {request.instruction}\n\n"
            f"Return ONLY the refined text, no explanations or markdown formatting."
        )

    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    ]

    refined = ""
    try:
        async for event in llm_service.chat_completion(
            messages=messages,
            system="You are a precise text editor. Return only the requested text, nothing else.",
        ):
            if event["type"] == "text_delta":
                refined += event["text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM refinement failed: {e}")

    return RefineResponse(refined_text=refined.strip())
