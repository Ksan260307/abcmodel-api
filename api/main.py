from fastapi import FastAPI, Header, HTTPException
import os

app = FastAPI(title="ABC Model Core API", version="3.0.0")

REQUIRED_KEY = os.environ.get("API_KEY")  # Railway Variables で設定

@app.middleware("http")
async def api_key_guard(request, call_next):
    key = request.headers.get("x-api-key")
    if REQUIRED_KEY and key != REQUIRED_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await call_next(request)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}