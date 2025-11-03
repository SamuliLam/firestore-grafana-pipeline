from fastapi import FastAPI, Request
from datetime import datetime
import json

app = FastAPI(title="Firestore Webhook Logger")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/webhook")
async def firestore_webhook(request: Request):
    """
    Receive any data and log it to a txt file
    """
    try:
        # Get the raw body as text
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Also try to parse as JSON for pretty printing
        try:
            data = json.loads(body_str)
            data_str = json.dumps(data, indent=2)
        except:
            data_str = body_str
        
        # Get headers
        headers = dict(request.headers)
        
        # Create log message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"""
{'='*80}
TIMESTAMP: {timestamp}
{'='*80}
HEADERS:
{json.dumps(headers, indent=2)}

BODY:
{data_str}
{'='*80}

"""
        
        # Write to file
        with open("webhook_logs.txt", "a") as f:
            f.write(log_message)
        
        print(log_message)  # Also print to console
        
        return {"status": "logged"}
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
