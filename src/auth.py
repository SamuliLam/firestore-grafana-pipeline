import os
from fastapi_plugin.fast_api_client import Auth0FastAPI

auth0 = Auth0FastAPI(
    domain=os.getenv("AUTH0_DOMAIN"),
    audience=os.getenv("AUTH0_AUDIENCE")
)