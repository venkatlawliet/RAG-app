"""All OpenAI Responses + Vector Store surface area lives here.

Module 2 deletes this file when we replace managed RAG with our own pipeline.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import AsyncIterator

from openai import AsyncOpenAI

from .config import get_settings
from .observability import traceable


@lru_cache
def client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().OPENAI_API_KEY)


@traceable(name="openai.vector_store.create")
async def create_vector_store(name: str) -> str:
    vs = await client().vector_stores.create(name=name)
    return vs.id


@traceable(name="openai.vector_store.upload_file")
async def upload_file_to_vector_store(
    vector_store_id: str, filename: str, content: bytes
) -> dict:
    file_obj = await client().files.create(
        file=(filename, content),
        purpose="assistants",
    )
    vs_file = await client().vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=file_obj.id,
    )
    return {"file_id": file_obj.id, "vector_store_file_id": vs_file.id, "status": vs_file.status}


@traceable(name="openai.vector_store.file_status")
async def vector_store_file_status(vector_store_id: str, file_id: str) -> str:
    f = await client().vector_stores.files.retrieve(
        vector_store_id=vector_store_id, file_id=file_id
    )
    return f.status


@traceable(name="openai.vector_store.delete_file")
async def delete_file(vector_store_id: str, file_id: str) -> None:
    try:
        await client().vector_stores.files.delete(
            vector_store_id=vector_store_id, file_id=file_id
        )
    except Exception:
        pass
    try:
        await client().files.delete(file_id)
    except Exception:
        pass


@traceable(name="openai.responses.stream")
async def stream_message(
    *,
    user_text: str,
    previous_response_id: str | None,
    vector_store_id: str | None,
    model: str,
) -> AsyncIterator[str]:
    """Yield SSE-formatted text chunks; final event includes the response id."""
    tools = []
    if vector_store_id:
        tools.append({"type": "file_search", "vector_store_ids": [vector_store_id]})

    kwargs: dict = {
        "model": model,
        "input": user_text,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id
    if tools:
        kwargs["tools"] = tools

    response_id: str | None = None
    async with client().responses.stream(**kwargs) as stream:
        async for event in stream:
            etype = getattr(event, "type", "")
            if etype == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                if delta:
                    yield _sse("delta", {"text": delta})
            elif etype == "response.completed":
                resp = getattr(event, "response", None)
                if resp is not None:
                    response_id = getattr(resp, "id", None)
            elif etype == "response.error":
                err = getattr(event, "error", None)
                yield _sse("error", {"message": str(err)})

        if response_id is None:
            final = await stream.get_final_response()
            response_id = getattr(final, "id", None)

    yield _sse("done", {"response_id": response_id})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
