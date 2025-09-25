import os

from fastapi import FastAPI
from health_imaging.lifespan import lifespan
from health_imaging.views import router

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = FastAPI(lifespan=lifespan)
app.include_router(router)
