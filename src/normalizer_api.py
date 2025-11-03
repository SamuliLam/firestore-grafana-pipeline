from fastapi import FastAPI, Request
import json
from src.db import insert_sensor_rows, init_db
from src.utils import normalize_sensor_data
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized")
    yield
    print("Application shutting down")


app = FastAPI(title="Normalizer-API", lifespan=lifespan)


@app.post("/webhook")
async def firestore_webhook(request: Request):
    try:
        body = await request.body()
        body_str = body.decode('utf-8')

        try:
            data = json.loads(body_str)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}

        print("Received webhook")
        print(json.dumps(data, indent=2))

        rows = normalize_sensor_data(data)
        if rows:
            insert_sensor_rows(rows)

        return {"status": "ok", "inserted": len(rows)}

    except Exception as e:
        print(f"Webhook erre: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
