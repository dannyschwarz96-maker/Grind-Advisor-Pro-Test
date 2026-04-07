from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import auth, beans, shots, predict, imports

app = FastAPI(title="Grind Advisor Cloud API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://grind-advisor-pro-test.vercel.app",
        "https://grind-advisor-pro-test-v1.vercel.app",
        "https://grind-advisor-pro-test-git-6779f3-dannyschwarz96-5700s-projects.vercel.app",
        "https://grind-advisor-pro-test-v1-lg7w3wobc.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

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
