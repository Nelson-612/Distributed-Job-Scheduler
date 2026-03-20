from fastapi import FastAPI
from api.routes import router
from db.database import engine
from db import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Distributed Job Scheduler")
app.include_router(router)

@app.get("/health")
def health():
    return { "status": "ok" }