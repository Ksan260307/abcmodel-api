from fastapi import FastAPI, Header, HTTPException
import os

import sentry_sdk
sentry_sdk.init(
        dsn="https://8fa50b5006ec68c0b279b6240096150d@o4511001948061696.ingest.de.sentry.io/4511001955205200",
    traces_sample_rate=0.1,  # 本番は 0.05〜0.2 程度に
    send_default_pii=True
)

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