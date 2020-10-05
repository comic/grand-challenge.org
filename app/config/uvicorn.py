from uvicorn.workers import UvicornWorker as BaseUvicornWorker


class UvicornWorker(BaseUvicornWorker):
    # Turn off lifespan as this causes an exception
    # https://code.djangoproject.com/ticket/31508
    CONFIG_KWARGS = {"loop": "uvloop", "http": "httptools", "lifespan": "off"}
