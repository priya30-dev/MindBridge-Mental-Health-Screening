"""Shared in-process state (loaded ML models). Kept separate from api.main
so routers can import it without circular imports."""

models = {}
