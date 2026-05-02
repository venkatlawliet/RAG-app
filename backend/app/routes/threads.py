from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..auth import AuthUser, require_user
from ..config import get_settings
from ..db import user_client
from .. import openai_responses

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ThreadCreate(BaseModel):
    title: str | None = None


class ThreadOut(BaseModel):
    id: str
    title: str | None
    last_response_id: str | None
    vector_store_id: str | None
    created_at: str


class MessageIn(BaseModel):
    content: str


async def _ensure_vector_store(db, user_id: str) -> str:
    existing = (
        db.table("user_settings")
        .select("vector_store_id")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if existing and existing.data and existing.data.get("vector_store_id"):
        return existing.data["vector_store_id"]
    vs_id = await openai_responses.create_vector_store(name=f"user-{user_id}")
    db.table("user_settings").upsert(
        {"user_id": user_id, "vector_store_id": vs_id}
    ).execute()
    return vs_id


@router.get("/threads", response_model=list[ThreadOut])
def list_threads(user: AuthUser = Depends(require_user)):
    db = user_client(user.token)
    res = (
        db.table("chat_threads")
        .select("id,title,last_response_id,vector_store_id,created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


@router.post("/threads", response_model=ThreadOut)
async def create_thread(body: ThreadCreate, user: AuthUser = Depends(require_user)):
    db = user_client(user.token)
    vs_id = await _ensure_vector_store(db, user.user_id)
    res = (
        db.table("chat_threads")
        .insert(
            {
                "user_id": user.user_id,
                "title": body.title or "New chat",
                "vector_store_id": vs_id,
            }
        )
        .execute()
    )
    if not res.data:
        raise HTTPException(500, "Failed to create thread")
    return res.data[0]


@router.post("/threads/{thread_id}/messages")
async def post_message(
    thread_id: str,
    body: MessageIn,
    user: AuthUser = Depends(require_user),
):
    db = user_client(user.token)
    thread_res = (
        db.table("chat_threads")
        .select("id,last_response_id,vector_store_id")
        .eq("id", thread_id)
        .maybe_single()
        .execute()
    )
    if not thread_res or not thread_res.data:
        raise HTTPException(404, "Thread not found")
    thread = thread_res.data
    settings = get_settings()

    async def event_stream():
        last_id: str | None = None
        async for chunk in openai_responses.stream_message(
            user_text=body.content,
            previous_response_id=thread.get("last_response_id"),
            vector_store_id=thread.get("vector_store_id"),
            model=settings.OPENAI_MODEL,
        ):
            yield chunk
            if "event: done" in chunk:
                import json as _json
                payload = chunk.split("data: ", 1)[1].strip()
                try:
                    last_id = _json.loads(payload).get("response_id")
                except Exception:
                    last_id = None
        if last_id:
            db.table("chat_threads").update({"last_response_id": last_id}).eq(
                "id", thread_id
            ).execute()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
