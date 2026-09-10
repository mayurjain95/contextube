from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import video

app = FastAPI(title="ContexTube")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before deploying anywhere real
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
