from fastapi import FastAPI
from health_imaging.lifespan import lifespan
from health_imaging.views import router

app = FastAPI(lifespan=lifespan)
app.include_router(router)
