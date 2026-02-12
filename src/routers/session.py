from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from src.dependencies import get_auth_claims
import secrets

router = APIRouter(prefix="/api/session", tags=["session"])
SESSION_STORE = {}


@router.post("/init")
def init_session(
        # Keep 'response' here even if using JSONResponse as a backup
        response: Response,
        claims: dict = Depends(get_auth_claims),
):
    # If the code reaches here, the dependency SUCCEEDED.
    # If it returns 400 before this, the error is inside get_auth_claims.
    email_claim = "https://envidata-api.metropolia.fi/email"
    user_email = claims.get(email_claim)


    if not user_email:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Email missing from token"})

    session_id = secrets.token_urlsafe(32)
    SESSION_STORE[session_id] = {
        "email": user_email,
        "name": claims.get("name", user_email),
    }

    # Prepare final response
    res = JSONResponse(content={"status": "ok"})

    # Set cookie on the NEW JSONResponse object 'res'
    res.set_cookie(
        key="backend_session",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )

    return res