import os

from .config import get_settings


def configure_langsmith() -> None:
    s = get_settings()
    if not s.LANGSMITH_TRACING or not s.LANGSMITH_API_KEY:
        os.environ["LANGSMITH_TRACING"] = "false"
        return
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = s.LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = s.LANGSMITH_PROJECT


try:
    from langsmith import traceable
except ImportError:
    def traceable(*args, **kwargs):
        def decorator(fn):
            return fn
        if args and callable(args[0]):
            return args[0]
        return decorator
