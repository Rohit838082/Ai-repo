from fastapi import APIRouter
from . import database as db

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
def dashboard_stats():
    return db.get_stats()

@router.get("/users")
def list_users():
    return db.get_all_users()

@router.get("/logs")
def list_build_logs():
    return db.get_all_build_logs()
