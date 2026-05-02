from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth import AuthUser, require_user
from ..db import user_client
from .. import openai_responses

router = APIRouter(prefix="/api/files", tags=["files"])


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


@router.get("")
def list_files(user: AuthUser = Depends(require_user)):
    db = user_client(user.token)
    res = (
        db.table("uploaded_files")
        .select("id,filename,bytes,openai_file_id,status,created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


@router.post("")
async def upload(file: UploadFile = File(...), user: AuthUser = Depends(require_user)):
    db = user_client(user.token)
    vs_id = await _ensure_vector_store(db, user.user_id)
    content = await file.read()
    result = await openai_responses.upload_file_to_vector_store(
        vector_store_id=vs_id, filename=file.filename or "upload.bin", content=content
    )
    row = (
        db.table("uploaded_files")
        .insert(
            {
                "user_id": user.user_id,
                "openai_file_id": result["file_id"],
                "openai_vector_store_id": vs_id,
                "filename": file.filename,
                "bytes": len(content),
                "status": result["status"] or "in_progress",
            }
        )
        .execute()
    )
    if not row.data:
        raise HTTPException(500, "Failed to record upload")
    return row.data[0]


@router.get("/{file_id}/status")
async def file_status(file_id: str, user: AuthUser = Depends(require_user)):
    db = user_client(user.token)
    res = (
        db.table("uploaded_files")
        .select("id,openai_file_id,openai_vector_store_id,status")
        .eq("id", file_id)
        .maybe_single()
        .execute()
    )
    if not res or not res.data:
        raise HTTPException(404, "File not found")
    row = res.data
    status = await openai_responses.vector_store_file_status(
        row["openai_vector_store_id"], row["openai_file_id"]
    )
    if status != row["status"]:
        db.table("uploaded_files").update({"status": status}).eq("id", file_id).execute()
    return {"id": file_id, "status": status}


@router.delete("/{file_id}")
async def delete_file(file_id: str, user: AuthUser = Depends(require_user)):
    db = user_client(user.token)
    res = (
        db.table("uploaded_files")
        .select("openai_file_id,openai_vector_store_id")
        .eq("id", file_id)
        .maybe_single()
        .execute()
    )
    if not res or not res.data:
        raise HTTPException(404, "File not found")
    await openai_responses.delete_file(
        res.data["openai_vector_store_id"], res.data["openai_file_id"]
    )
    db.table("uploaded_files").delete().eq("id", file_id).execute()
    return {"ok": True}
