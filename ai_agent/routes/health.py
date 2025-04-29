from fastapi import APIRouter # type: ignore

health_router = APIRouter()

@health_router.get("/health")
def health():
    return {"status": "ok"}
