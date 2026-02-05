from fastapi import FastAPI, HTTPException
from src.errors import (
    http_exception_handler,
    unhandled_exception_handler,
)
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.db import init_db
from src.routers import sensors, webhook, history



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized")
    yield
    print("Application shutting down")


app = FastAPI(
    title="Normalizer-API",
    description="API for normalizing and storing sensor data",
    version="1.0.0",
    lifespan=lifespan
)


app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.trust_proxy = True


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Check if the API is running"""
    return {"status": "ok"}


# Include routers
app.include_router(sensors.router)
app.include_router(webhook.router)
app.include_router(history.router)


if __name__ == "__main__":
    import subprocess
    import time

    print("Starting FastAPI server...")
    server_process = subprocess.Popen([
        'uvicorn', 'normalizer_api:app', '--host', '0.0.0.0', '--port', '8080', '--reload'
    ])
    time.sleep(2)
    if server_process.poll() is not None:
        print("ERROR: FastAPI server failed to start!")
        exit(1)
    print("FastAPI server started!")
    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server_process.terminate()
        server_process.wait()
        print("Shutdown complete")