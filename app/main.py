from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Inceptrix Red Team Engine")

app.include_router(router)
