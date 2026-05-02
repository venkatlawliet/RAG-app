from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthUser, require_user
from .config import get_settings
from .observability import configure_langsmith
from .routes import files as files_routes
from .routes import threads as threads_routes

configure_langsmith()
settings = get_settings()

app = FastAPI(title="Agentic RAG — Module 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/me")
def me(user: AuthUser = Depends(require_user)):
    return {"user_id": user.user_id, "email": user.email}


app.include_router(threads_routes.router)
app.include_router(files_routes.router)
