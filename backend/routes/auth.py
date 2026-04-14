from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from . import database as db

router = APIRouter(prefix="/api/auth", tags=["auth"])

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class UpgradeRequest(BaseModel):
    plan: str = "pro"

# ─── Auth middleware helper ─────────────────────────────

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token.")
    token = authorization.replace("Bearer ", "")
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token.")
    return user

# ─── Routes ─────────────────────────────────────────────

@router.post("/signup")
def signup(req: SignupRequest):
    result = db.create_user(req.email, req.password, req.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"token": result["token"], "message": "Account created."}

@router.post("/login")
def login(req: LoginRequest):
    result = db.login_user(req.email, req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return {"token": result["token"], "plan": result["plan"], "name": result["name"]}

@router.get("/me")
def profile(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    return {
        "email": user["email"],
        "name": user["name"],
        "plan": user["plan"],
        "daily_requests": user["daily_requests"]
    }

@router.post("/upgrade")
def upgrade(req: UpgradeRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    db.upgrade_plan(user["id"], req.plan)
    return {"message": f"Upgraded to {req.plan}.", "plan": req.plan}
