import logging
from fastapi import FastAPI
from api.routes import router
from db.database import engine
from db import models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Distributed Job Scheduler")
app.include_router(router)