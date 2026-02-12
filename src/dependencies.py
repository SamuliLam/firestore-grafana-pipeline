from fastapi import Depends, HTTPException, status
from src.auth import auth0

ADMIN_CLAIM = "https://envidata-api.metropolia.fi/admin"


def get_auth_claims(
        claims: dict = Depends(auth0.require_auth()),
) -> dict:
    print("Decoded JWT claims:", claims)
    return claims


def require_admin(
        claims: dict = Depends(get_auth_claims),
) -> dict:
    if not claims.get(ADMIN_CLAIM, False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return claims
