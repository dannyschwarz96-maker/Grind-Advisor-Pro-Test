from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import auth, beans, shots, predict, imports

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Grind Advisor Cloud API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"name": "Grind Advisor Cloud API", "docs": "/docs"}

app.include_router(auth.router, prefix="/api")
app.include_router(beans.router, prefix="/api")
app.include_router(shots.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
