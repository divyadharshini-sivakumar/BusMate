"""Auth routes – demo mode + Supabase JWT verification."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.models.schemas import SignInRequest, SignUpRequest, UserOut, UserRole
from app.services import demo_data
from app.services.supabase_client import get_supabase, is_demo

router = APIRouter()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_demo_role: Optional[str] = Header(None, alias="X-Demo-Role"),
) -> dict:
    """Extract user from Bearer token or demo header."""
    if is_demo():
        if (x_demo_role or "").lower() == "admin":
            return demo_data.DEMO_USERS["user-admin-demo"]
        return demo_data.DEMO_USERS["user-passenger-demo"]

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    sb = get_supabase()
    if not sb:
        raise HTTPException(503, "Auth service unavailable")
    try:
        user = sb.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(401, "Invalid token")
        # Fetch profile role from profiles table
        profile = (
            sb.table("profiles")
            .select("*")
            .eq("id", user.user.id)
            .single()
            .execute()
        )
        data = profile.data or {}
        return {
            "id": user.user.id,
            "email": user.user.email,
            "full_name": data.get("full_name", ""),
            "role": data.get("role", "passenger"),
            "phone": data.get("phone"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, f"Auth failed: {e}") from e


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != UserRole.ADMIN.value and user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user


@router.post("/signup", response_model=UserOut)
async def signup(body: SignUpRequest):
    if is_demo():
        uid = f"user-{body.email.split('@')[0]}"
        user = {
            "id": uid,
            "email": body.email,
            "full_name": body.full_name,
            "role": body.role.value,
            "phone": body.phone,
        }
        demo_data.DEMO_USERS[uid] = user
        return UserOut(**user)

    sb = get_supabase()
    if not sb:
        raise HTTPException(503, "Auth service unavailable")
    try:
        res = sb.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
                "options": {
                    "data": {
                        "full_name": body.full_name,
                        "role": body.role.value,
                        "phone": body.phone,
                    }
                },
            }
        )
        if not res.user:
            raise HTTPException(400, "Signup failed")
        # Profile created via trigger
        return UserOut(
            id=res.user.id,
            email=body.email,
            full_name=body.full_name,
            role=body.role,
            phone=body.phone,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/signin", response_model=UserOut)
async def signin(body: SignInRequest):
    if is_demo():
        for u in demo_data.DEMO_USERS.values():
            if u["email"] == body.email:
                return UserOut(**u)
        # auto-create demo passenger
        uid = f"user-{body.email.split('@')[0]}"
        user = {
            "id": uid,
            "email": body.email,
            "full_name": body.email.split("@")[0].title(),
            "role": "passenger",
            "phone": None,
        }
        demo_data.DEMO_USERS[uid] = user
        return UserOut(**user)

    sb = get_supabase()
    if not sb:
        raise HTTPException(503, "Auth service unavailable")
    try:
        res = sb.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        if not res.user:
            raise HTTPException(401, "Invalid credentials")
        profile = (
            sb.table("profiles")
            .select("*")
            .eq("id", res.user.id)
            .single()
            .execute()
        )
        data = profile.data or {}
        return UserOut(
            id=res.user.id,
            email=res.user.email or body.email,
            full_name=data.get("full_name", ""),
            role=UserRole(data.get("role", "passenger")),
            phone=data.get("phone"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, str(e)) from e


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return UserOut(**user)
